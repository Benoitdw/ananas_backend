"""Point d'entree du worker: planification quotidienne + CLI de mise au point.

    python -m ananas.worker.main                      # daemon planifie
    python -m ananas.worker.main --now                # scrape + notify tout de suite
    python -m ananas.worker.main --scrape-only --company qbd-group
    python -m ananas.worker.main --notify-only
    python -m ananas.worker.main --list-scrapers
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import UTC, datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

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
    """Une passe complete. C'est ce que declenche le cron, et ce que --now appelle."""
    started = datetime.now(UTC)

    with session_scope() as db:
        if scrape:
            run_scrapes(db, only=company)

        if notify:
            # On borne aux offres apparues pendant ce run pour ne pas deverser
            # tout l'historique... sauf au tout premier run, ou il n'y a rien
            # eu avant et ou l'utilisateur veut voir ce qui existe deja.
            since = started if scrape and _has_previous_run(db, before=started) else None
            report = send_daily_digests(db, since=since)
            log.info(
                "Notifications: %d envois, %d utilisateurs, %d offres%s",
                report.sent,
                report.users_notified,
                report.jobs_notified,
                f", {len(report.errors)} erreurs" if report.errors else "",
            )


def _has_previous_run(db, before: datetime) -> bool:
    from sqlalchemy import select

    stmt = select(ScrapeRun.id).where(
        ScrapeRun.started_at < before, ScrapeRun.finished_at.is_not(None)
    )
    return db.scalars(stmt.limit(1)).first() is not None


def start_scheduler() -> None:
    load_scrapers()
    load_notifiers()

    scheduler = BlockingScheduler(timezone=settings.timezone)
    trigger = CronTrigger(
        hour=settings.scrape_cron_hour,
        minute=settings.scrape_cron_minute,
        timezone=settings.timezone,
    )
    scheduler.add_job(
        daily_job,
        trigger=trigger,
        id="daily",
        # Un run rate (container arrete) n'est pas rattrape a l'allumage, et
        # deux runs ne peuvent pas se chevaucher.
        misfire_grace_time=3600,
        coalesce=True,
        max_instances=1,
    )
    log.info(
        "Worker demarre — passe quotidienne a %02d:%02d (%s). Prochaine execution: %s",
        settings.scrape_cron_hour,
        settings.scrape_cron_minute,
        settings.timezone,
        trigger.get_next_fire_time(None, datetime.now(scheduler.timezone)),
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
