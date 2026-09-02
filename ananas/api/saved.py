"""Entreprises enregistrees par l'utilisateur — ce qui declenche sa veille."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ananas.api.companies import _open_job_counts
from ananas.db import get_db
from ananas.models import Company, SavedCompany, User
from ananas.schemas import CompanyListItem, MessageOut
from ananas.scrapers.registry import get_scraper
from ananas.security import get_current_user

router = APIRouter(prefix="/api/me/companies", tags=["favoris"])


@router.get("", response_model=list[CompanyListItem])
def list_saved(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[CompanyListItem]:
    companies = db.scalars(
        select(Company)
        .join(SavedCompany, SavedCompany.company_id == Company.id)
        .where(SavedCompany.user_id == user.id)
        .order_by(Company.name)
    )
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
            is_saved=True,
            has_scraper=bool(c.scraper_key and get_scraper(c.scraper_key)),
            open_jobs=counts.get(c.id, 0),
        )
        for c in companies
    ]


@router.put("/{company_id}", response_model=MessageOut)
def save_company(
    company_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> MessageOut:
    """Idempotent: enregistrer deux fois n'est pas une erreur."""
    if db.get(Company, company_id) is None:
        raise HTTPException(404, "Entreprise inconnue")

    existing = db.get(SavedCompany, {"user_id": user.id, "company_id": company_id})
    if existing is None:
        db.add(SavedCompany(user_id=user.id, company_id=company_id))
        db.commit()
    return MessageOut(detail="Entreprise enregistree")


@router.delete("/{company_id}", response_model=MessageOut)
def unsave_company(
    company_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> MessageOut:
    existing = db.get(SavedCompany, {"user_id": user.id, "company_id": company_id})
    if existing is not None:
        db.delete(existing)
        db.commit()
    return MessageOut(detail="Entreprise retiree")
