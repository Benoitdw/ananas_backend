"""Repertoire d'entreprises: ce qui peuple la carte et le panneau de detail."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ananas.db import get_db
from ananas.models import Company, Job, SavedCompany, User
from ananas.schemas import CompanyDetail, CompanyFacets, CompanyListItem, JobOut
from ananas.security import get_current_user_optional
from ananas.scrapers.registry import get_scraper

router = APIRouter(prefix="/api/companies", tags=["entreprises"])


def _saved_ids(db: Session, user: User | None) -> set[int]:
    if user is None:
        return set()
    return set(db.scalars(select(SavedCompany.company_id).where(SavedCompany.user_id == user.id)))


def _open_job_counts(db: Session) -> dict[int, int]:
    rows = db.execute(
        select(Job.company_id, func.count(Job.id))
        .where(Job.closed_at.is_(None))
        .group_by(Job.company_id)
    )
    return dict(rows.all())


@router.get("", response_model=list[CompanyListItem])
def list_companies(
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
    q: str | None = Query(None, description="recherche libre: nom, ville, secteur, resume"),
    type: str | None = Query(None),
    core_business: str | None = Query(None),
    saved_only: bool = Query(False),
) -> list[CompanyListItem]:
    """Toute la carte en une requete: la charge utile est volontairement legere."""
    stmt = select(Company).order_by(Company.name)

    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Company.name.ilike(pattern),
                Company.city.ilike(pattern),
                Company.core_business.ilike(pattern),
                Company.baseline.ilike(pattern),
                Company.description.ilike(pattern),
            )
        )
    if type:
        stmt = stmt.where(Company.type == type)
    if core_business:
        # core_business est une liste separee par des virgules dans le CSV source
        stmt = stmt.where(Company.core_business.ilike(f"%{core_business}%"))

    saved = _saved_ids(db, user)
    if saved_only:
        if not saved:
            return []
        stmt = stmt.where(Company.id.in_(saved))

    counts = _open_job_counts(db)

    return [
        CompanyListItem(
            id=c.id,
            slug=c.slug,
            name=c.name,
            type=c.type,
            core_business=c.core_business,
            city=c.city,
            lat=c.lat,
            lon=c.lon,
            geo_precision=c.geo_precision,
            is_saved=c.id in saved,
            has_scraper=bool(c.scraper_key and get_scraper(c.scraper_key)),
            open_jobs=counts.get(c.id, 0),
        )
        for c in db.scalars(stmt)
    ]


@router.get("/facets", response_model=CompanyFacets)
def facets(db: Session = Depends(get_db)) -> CompanyFacets:
    """Valeurs distinctes pour les filtres de la sidebar."""
    types = sorted({t for t in db.scalars(select(Company.type).distinct()) if t})

    # core_business stocke plusieurs secteurs separes par des virgules;
    # la sidebar veut la liste a plat.
    sectors: set[str] = set()
    for raw in db.scalars(select(Company.core_business).distinct()):
        sectors.update(part.strip() for part in (raw or "").split(",") if part.strip())

    return CompanyFacets(types=types, core_businesses=sorted(sectors))


@router.get("/{company_id}", response_model=CompanyDetail)
def get_company(
    company_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
) -> CompanyDetail:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(404, "Entreprise inconnue")

    jobs = db.scalars(
        select(Job)
        .where(Job.company_id == company.id, Job.closed_at.is_(None))
        .order_by(Job.first_seen_at.desc())
    )

    detail = CompanyDetail.model_validate(company)
    detail.is_saved = company.id in _saved_ids(db, user)
    detail.jobs = [JobOut.model_validate(j) for j in jobs]
    return detail
