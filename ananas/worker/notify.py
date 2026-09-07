"""Envoi des digests quotidiens.

Regle produit: on ne notifie que les offres *nouvelles*, et seulement pour les
entreprises que l'utilisateur a enregistrees. Rien de nouveau = aucun message
(pas de "rien a signaler" quotidien).

Une notification envoyee ajoute un pied de page listant les entreprises
suivies sans scraper: leurs offres ne peuvent pas etre relevees toutes seules,
et le seul moyen de le savoir sinon serait de fouiller la carte. Ce pied de
page n'est jamais un message a lui seul — la regle "rien de nouveau, aucun
message" reste entiere.

Quand l'utilisateur a renseigne un profil, les offres sont triees par score de
correspondance et celles sous son seuil sont ecartees s'il l'a demande. Une
offre encore non caracterisee n'est jamais ecartee: on prefere un message de
trop a une offre manquee a cause d'une extraction en retard.

Meme regle pour le perimetre: qui a coche "seulement autour de chez moi" ne
recoit que les offres d'entreprises situees dans son rayon, mais une entreprise
sans coordonnees passe quand meme — position inconnue ne veut pas dire loin. Ce
qui a ete ecarte par le rayon est annonce en pied de message: un filtre
silencieux ferait croire a un jour sans offre.

L'idempotence repose sur ``sent_job_notifications``: la ligne n'est ecrite
qu'apres un envoi reussi, et sa cle primaire (user_id, job_id) empeche
structurellement le doublon. Relancer le worker dix fois dans la journee
n'enverra jamais deux fois la meme offre.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ananas.distance import distance_from
from ananas.models import (
    Company,
    Job,
    JobMatch,
    NotificationChannel,
    SavedCompany,
    SentJobNotification,
    User,
    UserHome,
    UserProfile,
)
from ananas.notifiers.base import Digest, JobLine, NotifierError
from ananas.notifiers.registry import get_notifier, load_notifiers
from ananas.scrapers.registry import get_scraper

log = logging.getLogger(__name__)


@dataclass
class NotifyReport:
    sent: int = 0
    users_notified: int = 0
    jobs_notified: int = 0
    errors: list[str] = field(default_factory=list)


def send_daily_digests(db: Session, since: datetime | None = None) -> NotifyReport:
    """``since`` limite aux offres vues pour la premiere fois apres cette date.

    Laisse a None, toutes les offres jamais notifiees sont envoyees — c'est le
    comportement voulu au premier run et quand un utilisateur vient
    d'enregistrer une entreprise deja scrapee.
    """
    load_notifiers()
    report = NotifyReport()

    channels = list(
        db.scalars(
            select(NotificationChannel)
            .join(User, User.id == NotificationChannel.user_id)
            .where(NotificationChannel.enabled.is_(True), User.is_active.is_(True))
        )
    )
    if not channels:
        log.info("Aucun canal de notification actif.")
        return report

    by_user: dict[int, list[NotificationChannel]] = {}
    for channel in channels:
        by_user.setdefault(channel.user_id, []).append(channel)

    for user_id, user_channels in by_user.items():
        jobs = pending_jobs(db, user_id, since=since)
        home = db.get(UserHome, user_id)
        jobs, beyond = within_radius(jobs, home)
        if not jobs:
            # Rien a envoyer: la regle "rien de neuf, aucun message" prime,
            # meme quand le rayon est seul responsable du vide. La page Offres
            # continue, elle, de tout montrer.
            continue

        digest = build_digest(
            jobs,
            unscraped=unscraped_saved_companies(db, user_id),
            beyond_radius=beyond,
            radius_km=home.radius_km if home else None,
        )
        delivered = False

        for channel in user_channels:
            notifier = get_notifier(channel.type)
            if notifier is None:
                report.errors.append(f"user {user_id}: transport '{channel.type}' inconnu")
                continue
            try:
                notifier.send(channel.target, digest)
            except NotifierError as exc:
                # On n'enregistre rien: les offres repasseront au prochain run.
                log.error("user %s / %s: %s", user_id, channel.type, exc)
                report.errors.append(f"user {user_id}: {exc}")
                continue

            channel.last_sent_at = datetime.now(UTC)
            report.sent += 1
            delivered = True

        if not delivered:
            continue

        # Marquage apres succes uniquement.
        for job, _company, _score in jobs:
            db.add(SentJobNotification(user_id=user_id, job_id=job.id))
        db.commit()

        report.users_notified += 1
        report.jobs_notified += len(jobs)
        log.info("user %s: %d offres notifiees", user_id, len(jobs))

    return report


def pending_jobs(
    db: Session, user_id: int, since: datetime | None = None
) -> list[tuple[Job, Company, int | None]]:
    """Offres ouvertes, chez une entreprise enregistree par l'utilisateur,
    jamais notifiees, triees par pertinence decroissante."""
    already_sent = select(SentJobNotification.job_id).where(
        SentJobNotification.user_id == user_id
    )
    profile = db.get(UserProfile, user_id)

    stmt = (
        select(Job, Company, JobMatch.score)
        .join(Company, Company.id == Job.company_id)
        .join(
            SavedCompany,
            (SavedCompany.company_id == Company.id) & (SavedCompany.user_id == user_id),
        )
        .outerjoin(JobMatch, (JobMatch.job_id == Job.id) & (JobMatch.user_id == user_id))
        .where(Job.closed_at.is_(None), Job.id.not_in(already_sent))
        .order_by(JobMatch.score.desc().nullslast(), Company.name, Job.first_seen_at.desc())
    )
    if since is not None:
        stmt = stmt.where(Job.first_seen_at >= since)

    rows = [(job, company, score) for job, company, score in db.execute(stmt)]

    if profile and profile.notify_only_relevant and profile.is_ready:
        # `score is None` = offre pas encore caracterisee: on la garde plutot
        # que de la perdre a cause d'une extraction en retard.
        rows = [r for r in rows if r[2] is None or r[2] >= profile.match_threshold]

    return rows


def within_radius(
    rows: list[tuple[Job, Company, int | None]], home: UserHome | None
) -> tuple[list[tuple[Job, Company, int | None]], int]:
    """Restreint le digest au perimetre, et dit combien d'offres sont sorties.

    Ne fait rien tant que l'utilisateur n'a pas coche le reglage, ou tant que
    son domicile n'a pas pu etre localise: filtrer sur un point inconnu
    reviendrait a tout supprimer.

    Une entreprise sans coordonnees est **gardee**, comme une offre non encore
    caracterisee l'est face au seuil de pertinence: on ne sait pas ou elle est,
    ce n'est pas une raison de la faire disparaitre.
    """
    if home is None or not home.notify_within_radius or home.point is None:
        return rows, 0

    kept = [
        row
        for row in rows
        if (d := distance_from(home.point, row[1].lat, row[1].lon)) is None
        or d <= home.radius_km
    ]
    return kept, len(rows) - len(kept)


def unscraped_saved_companies(db: Session, user_id: int) -> list[str]:
    """Entreprises suivies sans scraper qui fonctionne — ``scraper_key`` vide,
    ou renseigne mais introuvable dans le registre (cle perimee, module en
    erreur au chargement). Leurs offres ne sont jamais relevees toutes
    seules: c'est ce que la notification signale, pour que l'utilisateur
    sache ou aller regarder a la main plutot que de croire que "silence" veut
    dire "aucune offre".
    """
    stmt = (
        select(Company.name, Company.scraper_key)
        .join(SavedCompany, SavedCompany.company_id == Company.id)
        .where(SavedCompany.user_id == user_id)
        .order_by(Company.name)
    )
    return [
        name for name, scraper_key in db.execute(stmt) if not scraper_key or get_scraper(scraper_key) is None
    ]


def build_digest(
    jobs: list[tuple[Job, Company, int | None]],
    unscraped: list[str] | None = None,
    beyond_radius: int = 0,
    radius_km: int | None = None,
) -> Digest:
    """Regroupe par entreprise, en conservant l'ordre de pertinence.

    Le rendu concret appartient a chaque notifier.
    """
    companies: dict[str, list[JobLine]] = {}
    for job, company, score in jobs:
        companies.setdefault(company.name, []).append(
            JobLine(title=job.title, url=job.url, location=job.location, score=score)
        )
    return Digest(
        companies=companies,
        unscraped_companies=unscraped or [],
        beyond_radius=beyond_radius,
        radius_km=radius_km,
    )
