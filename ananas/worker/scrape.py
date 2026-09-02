"""Passe de scraping: interroge chaque entreprise branchee et met la base a jour.

Le point delicat est la detection de nouveaute. Une offre est *nouvelle* si son
couple (company_id, fingerprint) n'existe pas encore. Une offre deja connue voit
seulement son ``last_seen_at`` avance. Une offre connue mais absente du run est
*fermee* — mais uniquement si le scrape a reussi: sinon un site en panne
fermerait tout son catalogue d'un coup, et la reouverture le lendemain
declencherait une fausse notification pour chaque poste.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ananas.config import settings
from ananas.models import Company, Job, ScrapeRun
from ananas.scrapers.base import JobPosting, ScraperError
from ananas.scrapers.registry import get_scraper, load_scrapers

log = logging.getLogger(__name__)


@dataclass
class CompanyResult:
    company: str
    ok: bool
    found: int = 0
    new: int = 0
    closed: int = 0
    error: str | None = None


@dataclass
class ScrapeReport:
    run_id: int | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    results: list[CompanyResult] = field(default_factory=list)

    @property
    def ok(self) -> list[CompanyResult]:
        return [r for r in self.results if r.ok]

    @property
    def failed(self) -> list[CompanyResult]:
        return [r for r in self.results if not r.ok]

    @property
    def new_jobs(self) -> int:
        return sum(r.new for r in self.results)

    @property
    def closed_jobs(self) -> int:
        return sum(r.closed for r in self.results)


def scrapable_companies(db: Session, only: str | None = None) -> list[Company]:
    """Entreprises dont le scraper_key correspond a un scraper enregistre.

    ``only`` accepte un slug d'entreprise ou une cle de scraper, pour cibler
    une seule entreprise en developpement.
    """
    load_scrapers()
    stmt = select(Company).where(Company.scraper_key.is_not(None)).order_by(Company.name)
    if only:
        stmt = stmt.where((Company.scraper_key == only) | (Company.slug == only))

    companies = list(db.scalars(stmt))
    known, unknown = [], []
    for company in companies:
        (known if get_scraper(company.scraper_key) else unknown).append(company)

    for company in unknown:
        log.warning(
            "%s: scraper_key '%s' introuvable dans le registre — ignoree",
            company.name,
            company.scraper_key,
        )
    return known


def run_scrapes(db: Session, only: str | None = None) -> ScrapeReport:
    companies = scrapable_companies(db, only=only)
    report = ScrapeReport()

    run = ScrapeRun(started_at=report.started_at, companies_total=len(companies))
    db.add(run)
    db.commit()
    report.run_id = run.id

    if not companies:
        log.warning(
            "Aucune entreprise a scraper. Renseigne companies.scraper_key "
            "avec la cle d'un scraper enregistre."
        )

    for index, company in enumerate(companies):
        if index:
            time.sleep(settings.scrape_delay)  # politesse entre deux sites
        report.results.append(_scrape_one(db, company))

    run.finished_at = datetime.now(UTC)
    run.companies_ok = len(report.ok)
    run.companies_failed = len(report.failed)
    run.jobs_new = report.new_jobs
    run.jobs_closed = report.closed_jobs
    db.commit()

    log.info(
        "Scrape termine: %d/%d entreprises ok, %d nouvelles offres, %d fermees",
        len(report.ok),
        len(companies),
        report.new_jobs,
        report.closed_jobs,
    )
    return report


def _scrape_one(db: Session, company: Company) -> CompanyResult:
    scraper_cls = get_scraper(company.scraper_key)
    now = datetime.now(UTC)

    def failed(exc: Exception) -> CompanyResult:
        """Isole l'echec: on marque l'entreprise et on passe a la suivante.
        Surtout, on ne ferme aucune de ses offres."""
        log.error("%s: %s", company.name, exc)
        db.rollback()
        company.last_scraped_at = now
        company.last_scrape_status = "error"
        company.last_scrape_error = str(exc)[:2000]
        db.commit()
        return CompanyResult(company=company.name, ok=False, error=str(exc))

    try:
        postings = scraper_cls(company).run()
    except ScraperError as exc:
        return failed(exc)

    try:
        new, closed = _sync_jobs(db, company, postings, now)
    except Exception as exc:  # noqa: BLE001
        # Donnees inattendues (champ trop long, encodage): l'ecriture echoue
        # mais le run doit continuer, sinon une seule entreprise fait perdre
        # la passe quotidienne et la notification de tout le monde.
        return failed(exc)

    company.last_scraped_at = now
    company.last_scrape_status = "ok"
    company.last_scrape_error = None
    db.commit()

    return CompanyResult(
        company=company.name, ok=True, found=len(postings), new=new, closed=closed
    )


def _cut(value: str | None, length: int) -> str | None:
    return value[:length] if value else value


def _sync_jobs(
    db: Session, company: Company, postings: list[JobPosting], now: datetime
) -> tuple[int, int]:
    """Reconcilie les offres trouvees avec celles deja en base.

    Retourne (nombre de nouvelles, nombre de fermees).
    """
    existing = {
        job.fingerprint: job
        for job in db.scalars(select(Job).where(Job.company_id == company.id))
    }
    seen: set[str] = set()
    new_count = 0

    for posting in postings:
        fingerprint = posting.fingerprint
        seen.add(fingerprint)
        job = existing.get(fingerprint)

        if job is None:
            db.add(
                Job(
                    company_id=company.id,
                    fingerprint=fingerprint,
                    title=posting.title.strip()[:500],
                    url=posting.url[:1000],
                    # Troncatures defensives: un scraper tiers ne doit pas
                    # pouvoir faire echouer l'insertion de tout un lot.
                    location=_cut(posting.location, 255),
                    description=posting.description,
                    department=_cut(posting.department, 160),
                    posted_at=posting.posted_at,
                    first_seen_at=now,
                    last_seen_at=now,
                )
            )
            new_count += 1
            continue

        # Offre deja connue: on rafraichit les champs volatils sans toucher a
        # first_seen_at, qui est ce qui la rend "nouvelle" pour les notifications.
        job.last_seen_at = now
        job.title = posting.title.strip()[:500]
        job.url = posting.url[:1000]
        job.location = _cut(posting.location, 255)
        if posting.description:
            job.description = posting.description
        if posting.department:
            job.department = _cut(posting.department, 160)
        if posting.posted_at:
            job.posted_at = posting.posted_at
        # Une offre republiee apres avoir disparu: on la rouvre sans la
        # renotifier (sent_job_notifications garde la trace de l'envoi).
        job.closed_at = None

    closed_count = 0
    for fingerprint, job in existing.items():
        if fingerprint not in seen and job.closed_at is None:
            job.closed_at = now
            closed_count += 1

    db.flush()
    return new_count, closed_count
