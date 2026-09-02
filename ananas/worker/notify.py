"""Envoi des digests quotidiens.

Regle produit: on ne notifie que les offres *nouvelles*, et seulement pour les
entreprises que l'utilisateur a enregistrees. Rien de nouveau = aucun message
(pas de "rien a signaler" quotidien).

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

from ananas.models import (
    Company,
    Job,
    NotificationChannel,
    SavedCompany,
    SentJobNotification,
    User,
)
from ananas.notifiers.base import Digest, JobLine, NotifierError
from ananas.notifiers.registry import get_notifier, load_notifiers

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
        if not jobs:
            continue

        digest = build_digest(jobs)
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
        for job, _company in jobs:
            db.add(SentJobNotification(user_id=user_id, job_id=job.id))
        db.commit()

        report.users_notified += 1
        report.jobs_notified += len(jobs)
        log.info("user %s: %d offres notifiees", user_id, len(jobs))

    return report


def pending_jobs(
    db: Session, user_id: int, since: datetime | None = None
) -> list[tuple[Job, Company]]:
    """Offres ouvertes, chez une entreprise enregistree par l'utilisateur,
    jamais notifiees a cet utilisateur."""
    already_sent = select(SentJobNotification.job_id).where(
        SentJobNotification.user_id == user_id
    )

    stmt = (
        select(Job, Company)
        .join(Company, Company.id == Job.company_id)
        .join(
            SavedCompany,
            (SavedCompany.company_id == Company.id) & (SavedCompany.user_id == user_id),
        )
        .where(Job.closed_at.is_(None), Job.id.not_in(already_sent))
        .order_by(Company.name, Job.first_seen_at.desc())
    )
    if since is not None:
        stmt = stmt.where(Job.first_seen_at >= since)

    return [(job, company) for job, company in db.execute(stmt)]


def build_digest(jobs: list[tuple[Job, Company]]) -> Digest:
    """Regroupe par entreprise. Le rendu concret appartient a chaque notifier."""
    companies: dict[str, list[JobLine]] = {}
    for job, company in jobs:
        companies.setdefault(company.name, []).append(
            JobLine(title=job.title, url=job.url, location=job.location)
        )
    return Digest(companies=companies)
