"""Orchestration: quand extraire, quand rescorer.

Deux declencheurs, et c'est tout:

- une offre gagne des caracteristiques -> on score cette offre pour tous les
  profils prets;
- un profil est (re)extrait -> on score toutes les offres pour ce profil.

Le scoring lui-meme etant du Python pur et gratuit, on materialise **toutes**
les paires plutot que de calculer a la demande. C'est ce qui permet de trier
et filtrer en SQL: "les offres pertinentes de cette entreprise" devient un
simple WHERE score >= seuil.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ananas.ai.base import LLMError
from ananas.ai.extraction import extract_job, extract_profile
from ananas.ai.matching import score_job
from ananas.ai.registry import get_provider
from ananas.config import settings
from ananas.models import Job, JobFeatures, JobMatch, UserProfile

log = logging.getLogger(__name__)


def ai_ready() -> bool:
    provider = get_provider()
    return provider is not None and provider.is_configured()


# ------------------------------------------------------------------- offres


def extract_job_features(db: Session, job: Job) -> JobFeatures | None:
    """Extrait et enregistre les caracteristiques d'une offre. None si echec."""
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


def extract_missing_features(db: Session, limit: int | None = None) -> int:
    """Traite les offres ouvertes encore depourvues de caracteristiques."""
    if not ai_ready():
        log.info("Aucun modele configure: extraction ignoree.")
        return 0

    stmt = (
        select(Job)
        .outerjoin(JobFeatures, JobFeatures.job_id == Job.id)
        .where(Job.closed_at.is_(None), JobFeatures.job_id.is_(None))
        .order_by(Job.first_seen_at.desc())
    )
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
