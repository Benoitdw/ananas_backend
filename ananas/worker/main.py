"""Point d'entree du worker: planification quotidienne + CLI de mise au point.

    python -m ananas.worker.main                      # daemon planifie
    python -m ananas.worker.main --now                # scrape + notify tout de suite
    python -m ananas.worker.main --scrape-only --company qbd-group
    python -m ananas.worker.main --notify-only
    python -m ananas.worker.main --list-scrapers

**Deux passes planifiees, pas une.** Quand le fournisseur de modele fait du
lot (Gemini), l'extraction des offres est ce qui prend le plus longtemps et
le worker n'a pas a l'attendre en direct:

  - ``scrape_cron_hour/minute`` (minuit par defaut) — scrape, puis soumet un
    lot d'extraction pour tout ce qui manque encore de caracteristiques.
  - ``notify_cron_hour/minute`` (7h par defaut) — recolte le lot (le prend tel
    quel s'il n'est pas fini: mieux vaut notifier a l'heure avec deux ou trois
    offres non triees que faire attendre tout le monde), puis notifie.

Sans fournisseur a mode lot, la premiere passe extrait en direct comme avant
l'ajout du mode lot — rien ne change pour un fournisseur qui ne le propose pas.

Les commandes interactives (``--now``, ``--extract-only``, et le flux habituel
d'ajout d'un scraper: ``--scrape-only`` puis verification) restent, elles,
entierement synchrones via ``daily_job`` / ``extract_missing_features``: une
reponse immediate compte plus que le cout quand quelqu'un attend a l'ecran.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import UTC, datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from ananas.ai.registry import get_provider, load_providers
from ananas.ai.service import (
    collect_extraction_batches,
    extract_missing_features,
    submit_extraction_batch,
)
from ananas.config import settings
from ananas.db import session_scope
from ananas.models import ScrapeRun
from ananas.notifiers.registry import load_notifiers
from ananas.scrapers.registry import load_scrapers
from ananas.worker.notify import send_daily_digests
from ananas.worker.scrape import run_scrapes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ananas.worker")


def daily_job(company: str | None = None, scrape: bool = True, notify: bool = True) -> None:
    """Une passe complete, entierement synchrone. Ce que ``--now`` et les
    autres flags CLI appellent — jamais le mode lot, voir le docstring du
    module."""
    started = datetime.now(UTC)

    with session_scope() as db:
        if scrape:
            run_scrapes(db, only=company)
            # Les caracteristiques doivent exister avant la notification, sinon
            # le tri par pertinence n'a rien a trier.
            extract_missing_features(db)

        if notify:
            # On borne aux offres apparues pendant ce run pour ne pas deverser
            # tout l'historique... sauf au tout premier run, ou il n'y a rien
            # eu avant et ou l'utilisateur veut voir ce qui existe deja.
            since = started if scrape and _has_previous_run(db, before=started) else None
            report = send_daily_digests(db, since=since)
            _log_report(report)


def midnight_job() -> None:
    """Scrape, puis soumet un lot d'extraction si le fournisseur le permet.

    Ne notifie jamais — c'est le role de ``morning_job``, une fois le lot
    recolte (ou tout de suite si le fournisseur ne fait pas de lot).
    """
    with session_scope() as db:
        run_scrapes(db)

        provider = get_provider()
        if provider is not None and provider.is_configured() and provider.supports_batch():
            # Un lot d'une nuit precedente a pu finir entretemps: autant le
            # liberer maintenant, ses offres ne seront pas resoumises ce soir.
            collect_extraction_batches(db)
            batch = submit_extraction_batch(db)
            if batch:
                log.info("Lot d'extraction soumis pour la nuit: %d offres", len(batch.job_ids))
            else:
                log.info("Rien a soumettre en lot.")
        else:
            # Pas de mode lot chez ce fournisseur: comportement synchrone
            # d'origine, sinon les offres resteraient sans caracteristiques
            # jusqu'a ce que quelqu'un lance --extract-only a la main.
            extract_missing_features(db)


def morning_job() -> None:
    """Recolte le lot de la nuit (s'il y en a un), puis notifie.

    Tolerant par construction: un lot pas encore termine laisse ses offres
    sans caracteristiques — elles restent visibles, simplement non triees,
    dans la notification plutot que de la retarder.
    """
    with session_scope() as db:
        provider = get_provider()
        if provider is not None and provider.is_configured() and provider.supports_batch():
            collected = collect_extraction_batches(db)
            if collected:
                log.info("%d offres caracterisees par lot avant la notification", collected)

        latest = db.scalars(
            select(ScrapeRun).order_by(ScrapeRun.started_at.desc()).limit(1)
        ).first()
        since = None
        if latest is not None and _has_previous_run(db, before=latest.started_at):
            since = latest.started_at

        report = send_daily_digests(db, since=since)
        _log_report(report)


def _log_report(report) -> None:
    log.info(
        "Notifications: %d envois, %d utilisateurs, %d offres%s",
        report.sent,
        report.users_notified,
        report.jobs_notified,
        f", {len(report.errors)} erreurs" if report.errors else "",
    )


def _has_previous_run(db, before: datetime) -> bool:
    stmt = select(ScrapeRun.id).where(
        ScrapeRun.started_at < before, ScrapeRun.finished_at.is_not(None)
    )
    return db.scalars(stmt.limit(1)).first() is not None


def start_scheduler() -> None:
    load_scrapers()
    load_notifiers()
    load_providers()

    scheduler = BlockingScheduler(timezone=settings.timezone)

    scrape_trigger = CronTrigger(
        hour=settings.scrape_cron_hour,
        minute=settings.scrape_cron_minute,
        timezone=settings.timezone,
    )
    notify_trigger = CronTrigger(
        hour=settings.notify_cron_hour,
        minute=settings.notify_cron_minute,
        timezone=settings.timezone,
    )
    # coalesce + max_instances=1: un run rate (container arrete) n'est pas
    # rattrape a l'allumage, et deux runs du meme job ne se chevauchent pas.
    scheduler.add_job(
        midnight_job, trigger=scrape_trigger, id="scrape",
        misfire_grace_time=3600, coalesce=True, max_instances=1,
    )
    scheduler.add_job(
        morning_job, trigger=notify_trigger, id="notify",
        misfire_grace_time=3600, coalesce=True, max_instances=1,
    )
    now = datetime.now(scheduler.timezone)
    log.info(
        "Worker demarre — scrape+lot a %02d:%02d, notification a %02d:%02d (%s). "
        "Prochaines executions: %s / %s",
        settings.scrape_cron_hour, settings.scrape_cron_minute,
        settings.notify_cron_hour, settings.notify_cron_minute,
        settings.timezone,
        scrape_trigger.get_next_fire_time(None, now),
        notify_trigger.get_next_fire_time(None, now),
    )
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Arret du worker.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ananas-worker", description=__doc__)
    parser.add_argument("--now", action="store_true", help="execute une passe immediatement")
    parser.add_argument("--scrape-only", action="store_true", help="scrape sans notifier")
    parser.add_argument("--notify-only", action="store_true", help="notifie sans scraper")
    parser.add_argument(
        "--extract-only", action="store_true", help="caracterise les offres en attente"
    )
    parser.add_argument("--company", help="limite a une entreprise (slug ou scraper_key)")
    parser.add_argument(
        "--list-scrapers", action="store_true", help="affiche les scrapers enregistres"
    )
    args = parser.parse_args(argv)

    if args.list_scrapers:
        scrapers = load_scrapers()
        if not scrapers:
            print("Aucun scraper enregistre.")
        for key, cls in sorted(scrapers.items()):
            print(f"  {key:24} {cls.label or cls.__name__:24} {cls.careers_url}")
        return 0

    if args.extract_only:
        with session_scope() as db:
            print(f"{extract_missing_features(db)} offres caracterisees")
        return 0

    one_shot = args.now or args.scrape_only or args.notify_only or args.company
    if one_shot:
        daily_job(
            company=args.company,
            scrape=not args.notify_only,
            notify=not args.scrape_only,
        )
        return 0

    start_scheduler()
    return 0


if __name__ == "__main__":
    sys.exit(main())
