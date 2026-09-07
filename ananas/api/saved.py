"""Entreprises enregistrees ou masquees par l'utilisateur.

Deux reglages opposes sur la meme relation utilisateur/entreprise: enregistrer
declenche la veille, masquer la coupe entierement (carte, feed d'offres et
notification). Ils sont exclusifs, et c'est chaque route qui le garantit —
masquer retire des favoris, enregistrer demasque. L'invariant tient donc a
l'ecriture, ce qui evite d'avoir a arbitrer entre les deux tables a chaque
lecture.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ananas.api.companies import _open_job_counts
from ananas.db import get_db
from ananas.models import Company, HiddenCompany, SavedCompany, User
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


@router.get("/hidden", response_model=list[CompanyListItem])
def list_hidden(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[CompanyListItem]:
    """Ce que l'utilisateur a masque, pour pouvoir revenir dessus.

    Declaree avant `PUT /{company_id}`: sans cela "hidden" serait avale par le
    parametre de chemin.
    """
    companies = db.scalars(
        select(Company)
        .join(HiddenCompany, HiddenCompany.company_id == Company.id)
        .where(HiddenCompany.user_id == user.id)
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
            tags=c.tags,
            source=c.source,
            city=c.city,
            lat=c.lat,
            lon=c.lon,
            geo_precision=c.geo_precision,
            is_saved=False,
            is_hidden=True,
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

    # Enregistrer une entreprise masquee, c'est vouloir la revoir: on demasque
    # plutot que de laisser deux reglages contradictoires coexister.
    if (hidden := db.get(HiddenCompany, {"user_id": user.id, "company_id": company_id})) is not None:
        db.delete(hidden)

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


@router.put("/{company_id}/hidden", response_model=MessageOut)
def hide_company(
    company_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> MessageOut:
    """Masque une entreprise: plus rien de cette boite ne remonte a cet
    utilisateur — ni sur la carte, ni dans le feed d'offres, ni en
    notification. Idempotent: la masquer deux fois n'est pas une erreur.

    Retire aussi le favori s'il existait. Suivre et masquer voudraient dire
    l'inverse l'un de l'autre; l'action la plus recente gagne.
    """
    if db.get(Company, company_id) is None:
        raise HTTPException(404, "Entreprise inconnue")

    if (saved := db.get(SavedCompany, {"user_id": user.id, "company_id": company_id})) is not None:
        db.delete(saved)

    if db.get(HiddenCompany, {"user_id": user.id, "company_id": company_id}) is None:
        db.add(HiddenCompany(user_id=user.id, company_id=company_id))
    db.commit()
    return MessageOut(detail="Entreprise masquee")


@router.delete("/{company_id}/hidden", response_model=MessageOut)
def unhide_company(
    company_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> MessageOut:
    """Demasque sans re-enregistrer: l'entreprise revient sur la carte, mais
    l'utilisateur n'en avait pas forcement fait un favori avant."""
    existing = db.get(HiddenCompany, {"user_id": user.id, "company_id": company_id})
    if existing is not None:
        db.delete(existing)
        db.commit()
    return MessageOut(detail="Entreprise reaffichee")
