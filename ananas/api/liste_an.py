"""Onglet « Liste An »: les offres ouvertes des employeurs de la liste.

Pas de score ni de profil: juste le scraping, trie pour un profil
scientifique par ``ananas.liste_an``. Les offres ecartees sont renvoyees
aussi, avec leur raison, pour que l'interface puisse les montrer a la demande
— le filtre se trompe parfois, il ne doit rien cacher definitivement.

L'utilisateur peut aussi masquer une offre lui-meme (``PUT
/api/me/jobs/{id}/hidden``, la meme table que le feed): elle revient avec
``hidden=True`` et l'interface la range parmi les ecartees.
"""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ananas.db import get_db
from ananas.liste_an import Offer, exclusion_reason
from ananas.models import Company, HiddenJob, Job, User
from ananas.security import get_current_user

router = APIRouter(prefix="/api/liste-an", tags=["liste an"])


class ListeAnJob(BaseModel):
    id: int
    title: str
    url: str
    location: str | None
    department: str | None
    posted_at: date | None
    first_seen_at: datetime
    company_id: int
    company_name: str
    company_slug: str
    category: str
    # None = offre retenue; sinon pourquoi le filtre l'a ecartee
    excluded: str | None = None
    # Masquee par l'utilisateur (independant du filtre)
    hidden: bool = False


@router.get("/jobs", response_model=list[ListeAnJob])
def liste_an_jobs(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[ListeAnJob]:
    hidden_ids = select(HiddenJob.job_id).where(HiddenJob.user_id == user.id)
    stmt = (
        select(Job, Company, Job.id.in_(hidden_ids))
        .join(Company, Company.id == Job.company_id)
        .where(Company.liste_an_category.is_not(None), Job.closed_at.is_(None))
        .order_by(Job.first_seen_at.desc(), Job.id.desc())
    )
    return [
        ListeAnJob(
            id=job.id,
            title=job.title,
            url=job.url,
            location=job.location,
            department=job.department,
            posted_at=job.posted_at,
            first_seen_at=job.first_seen_at,
            company_id=company.id,
            company_name=company.name,
            company_slug=company.slug,
            category=company.liste_an_category or "",
            excluded=exclusion_reason(
                company.slug,
                Offer(job.title, job.location, job.department, job.description),
            ),
            hidden=bool(hidden),
        )
        for job, company, hidden in db.execute(stmt)
    ]
