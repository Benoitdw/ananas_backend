"""Orchestration: quand extraire, quand rescorer.

Deux declencheurs, et c'est tout:

- une offre gagne des caracteristiques -> on score cette offre pour tous les
  profils prets;
- un profil est (re)extrait -> on score toutes les offres pour ce profil.

Le scoring lui-meme etant du Python pur et gratuit, on materialise **toutes**
les paires plutot que de calculer a la demande. C'est ce qui permet de trier
et filtrer en SQL: "les offres pertinentes de cette entreprise" devient un
simple WHERE score >= seuil.

**Deux chemins pour caracteriser une offre**, choisis par l'appelant, pas par
ce module:

- ``extract_missing_features`` — synchrone, un appel modele par offre. Utilise
  par les commandes interactives (``--extract-only``, ``--now``, l'ajout d'un
  scraper en developpement): une reponse immediate compte plus que le cout,
  et le volume y est ponctuel.
- ``submit_extraction_batch`` / ``collect_extraction_batches`` — asynchrone,
  toutes les offres manquantes en un seul lot chez le fournisseur (moitie prix
  chez Gemini, mais sans delai garanti). Reserve au cycle automatique du
  worker (minuit: scrape + soumission : 7h : recolte + notification, voir
  ``ananas.worker.main``): personne n'attend a l'ecran, et le lot peut
  legitimement ne pas etre termine a l'heure de la notification — les offres
  encore sans caracteristiques y restent simplement non triees, et repartent
  dans le lot suivant.

Les deux ecrivent les memes lignes ``JobFeatures``, avec le meme nettoyage
(``ananas.ai.extraction.finalize_job_data``): aucune des deux n'est le chemin
"degrade", ce sont juste deux vitesses adaptees a deux contextes d'appel.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ananas.ai.base import LLMError
from ananas.ai.extraction import build_job_request, extract_job, extract_profile, finalize_job_data
from ananas.ai.matching import score_job
from ananas.ai.registry import get_provider
from ananas.config import settings
from ananas.models import ExtractionBatch, Job, JobFeatures, JobMatch, UserProfile

log = logging.getLogger(__name__)


def ai_ready() -> bool:
    provider = get_provider()
    return provider is not None and provider.is_configured()


# ------------------------------------------------------------------- offres


def _missing_features_query():
    return (
        select(Job)
        .outerjoin(JobFeatures, JobFeatures.job_id == Job.id)
        .where(Job.closed_at.is_(None), JobFeatures.job_id.is_(None))
        .order_by(Job.first_seen_at.desc())
    )


def _save_job_features(db: Session, job: Job, data: dict) -> JobFeatures:
    """Enregistre une reponse deja nettoyee (voir ``finalize_job_data``).
    Ne score pas: c'est a l'appelant de le faire, une fois pour chaque offre
    reussie, comme pour l'echec — voir ``extract_missing_features`` et
    ``collect_extraction_batches``."""
    features = job.features or JobFeatures(job_id=job.id)
    features.role_family = data["role_family"][:120]
    features.seniority = data["seniority"]
    features.years_experience_min = max(0, int(data.get("years_experience_min") or 0))
    features.contract = data["contract"]
    features.remote = data["remote"]
    features.skills = data["skills"]
    features.nice_to_have = data["nice_to_have"]
    features.domains = data["domains"]
    features.languages = data["languages"]
    features.locations = data["locations"]
    features.summary = data["summary"]
    features.model = settings.ai_model
    features.extracted_at = datetime.now(UTC)
    db.add(features)
    db.commit()
    return features


def extract_job_features(db: Session, job: Job) -> JobFeatures | None:
    """Extrait et enregistre les caracteristiques d'une offre, en direct.
    None si echec."""
    try:
        data = extract_job(
            title=job.title,
            company=job.company.name,
            location=job.location or "",
            department=job.department or "",
            description=job.description or "",
        )
    except LLMError as exc:
        # Une extraction ratee laisse l'offre sans caracteristiques: elle sera
        # reprise au prochain passage, sans bloquer les autres.
        log.warning("extraction impossible pour l'offre %s: %s", job.id, exc)
        return None

    return _save_job_features(db, job, data)


def extract_missing_features(db: Session, limit: int | None = None) -> int:
    """Traite en direct les offres ouvertes encore depourvues de
    caracteristiques — un appel modele par offre. Voir le docstring du module
    pour la difference avec le mode lot."""
    if not ai_ready():
        log.info("Aucun modele configure: extraction ignoree.")
        return 0

    stmt = _missing_features_query()
    if limit:
        stmt = stmt.limit(limit)

    jobs = list(db.scalars(stmt))
    done = 0
    for job in jobs:
        if extract_job_features(db, job) is not None:
            done += 1
            score_job_for_all(db, job)
    if jobs:
        log.info("Caracteristiques extraites: %d/%d offres", done, len(jobs))
    return done


# --------------------------------------------------------- offres, mode lot


def submit_extraction_batch(db: Session) -> ExtractionBatch | None:
    """Soumet en un seul lot toutes les offres ouvertes encore sans
    caracteristiques — sauf celles deja parties dans un lot pas encore
    recolte, pour ne pas les payer deux fois.

    None si le fournisseur configure ne fait pas de lot, ou s'il n'y a rien a
    soumettre. Ne leve jamais: un lot qui ne part pas ce soir repart demain,
    ce n'est pas une erreur qui doit interrompre le worker.
    """
    provider = get_provider()
    if provider is None or not provider.is_configured() or not provider.supports_batch():
        return None

    in_flight: set[int] = set()
    for batch in db.scalars(select(ExtractionBatch).where(ExtractionBatch.status == "pending")):
        in_flight.update(batch.job_ids)

    jobs = [j for j in db.scalars(_missing_features_query()) if j.id not in in_flight]
    if not jobs:
        return None

    items = [
        build_job_request(
            title=j.title,
            company=j.company.name,
            location=j.location or "",
            department=j.department or "",
            description=j.description or "",
        )
        for j in jobs
    ]

    try:
        provider_batch_id = provider.submit_batch(items)
    except LLMError as exc:
        log.error("soumission du lot d'extraction impossible: %s", exc)
        return None

    batch = ExtractionBatch(
        provider=provider.key, provider_batch_id=provider_batch_id, job_ids=[j.id for j in jobs]
    )
    db.add(batch)
    db.commit()
    log.info("lot d'extraction soumis (%s): %d offres", provider_batch_id, len(jobs))
    return batch


def collect_extraction_batches(db: Session) -> int:
    """Recolte les lots en attente aupres du fournisseur, applique ceux qui
    sont termines. Retourne le nombre d'offres caracterisees.

    Un lot pas encore termine est laisse tel quel — ses offres restent sans
    caracteristiques et repartiront dans le prochain lot soumis. C'est
    deliberement tolerant: mieux vaut notifier a l'heure avec deux ou trois
    offres non triees que retarder tout le monde en attendant un lot qui peut,
    dans le pire des cas, prendre jusqu'a 24h.
    """
    provider = get_provider()
    if provider is None or not provider.is_configured() or not provider.supports_batch():
        return 0

    pending = list(db.scalars(select(ExtractionBatch).where(ExtractionBatch.status == "pending")))
    total_done = 0

    for batch in pending:
        try:
            poll = provider.poll_batch(batch.provider_batch_id)
        except LLMError as exc:
            log.warning("lot %s illisible (%s), on reessaiera", batch.provider_batch_id, exc)
            continue

        if poll.state == "pending":
            log.info("lot %s pas encore termine, reporte au prochain passage", batch.provider_batch_id)
            continue

        if poll.state != "succeeded" or poll.results is None:
            batch.status = "failed"
            batch.collected_at = datetime.now(UTC)
            db.commit()
            continue

        done = 0
        for job_id, data in zip(batch.job_ids, poll.results, strict=False):
            if data is None:
                continue  # cette offre precise a echoue au sein du lot: retentee au prochain lot
            job = db.get(Job, job_id)
            if job is None or job.closed_at is not None:
                continue  # fermee ou supprimee entre-temps: sans objet
            _save_job_features(db, job, finalize_job_data(data))
            score_job_for_all(db, job)
            done += 1

        batch.status = "collected"
        batch.collected_at = datetime.now(UTC)
        db.commit()
        log.info(
            "lot %s recolte: %d/%d offres caracterisees",
            batch.provider_batch_id, done, len(batch.job_ids),
        )
        total_done += done

    return total_done


# ------------------------------------------------------------------ profils


def extract_user_profile(db: Session, profile: UserProfile) -> UserProfile:
    """(Re)structure le CV et les aspirations, puis rescore tout pour cet
    utilisateur. L'echec est enregistre sur le profil, pas leve."""
    try:
        profile.data = extract_profile(cv=profile.cv_text, aspirations=profile.aspirations)
        profile.status = "ok"
        profile.error = None
        profile.version += 1
    except LLMError as exc:
        profile.status = "error"
        profile.error = str(exc)[:1000]
        db.commit()
        return profile

    profile.model = settings.ai_model
    profile.extracted_at = datetime.now(UTC)
    db.commit()

    score_all_for_user(db, profile)
    return profile


# ----------------------------------------------------------------- scoring


def _upsert(db: Session, user_id: int, job_id: int, profile_version: int, result) -> None:
    match = db.get(JobMatch, {"user_id": user_id, "job_id": job_id})
    if match is None:
        match = JobMatch(user_id=user_id, job_id=job_id)
        db.add(match)
    match.score = result.score
    match.reasons = result.reasons
    match.profile_version = profile_version
    match.computed_at = datetime.now(UTC)


def score_all_for_user(db: Session, profile: UserProfile) -> int:
    """Rescore toutes les offres ouvertes pour un profil."""
    if not profile.is_ready:
        return 0

    rows = db.execute(
        select(Job.id, JobFeatures).join(JobFeatures, JobFeatures.job_id == Job.id)
        .where(Job.closed_at.is_(None))
    ).all()

    for job_id, features in rows:
        _upsert(db, profile.user_id, job_id, profile.version, score_job(profile.data, features.as_dict()))
    db.commit()
    log.info("%d offres scorees pour l'utilisateur %s", len(rows), profile.user_id)
    return len(rows)


def score_job_for_all(db: Session, job: Job) -> int:
    """Score une offre fraichement caracterisee pour tous les profils prets."""
    if job.features is None:
        return 0

    features = job.features.as_dict()
    profiles = [p for p in db.scalars(select(UserProfile)) if p.is_ready]
    for profile in profiles:
        _upsert(db, profile.user_id, job.id, profile.version, score_job(profile.data, features))
    db.commit()
    return len(profiles)


def rescore_stale(db: Session) -> int:
    """Rattrape les paires dont le score date d'une version anterieure du
    profil — utile apres un echec partiel."""
    total = 0
    for profile in db.scalars(select(UserProfile)):
        if profile.is_ready:
            total += score_all_for_user(db, profile)
    return total
