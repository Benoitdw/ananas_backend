"""Feed des offres — le pendant web de la notification quotidienne."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ananas.db import get_db
from ananas.models import Company, Job, SavedCompany, User
from ananas.schemas import JobWithCompany
from ananas.security import get_current_user

router = APIRouter(prefix="/api/me/jobs", tags=["offres"])


@router.get("", response_model=list[JobWithCompany])
def my_jobs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    include_closed: bool = Query(False, description="inclure les offres disparues du site"),
    limit: int = Query(200, le=1000),
) -> list[JobWithCompany]:
    stmt = (
        select(Job, Company)
        .join(Company, Company.id == Job.company_id)
        .join(
            SavedCompany,
            (SavedCompany.company_id == Company.id) & (SavedCompany.user_id == user.id),
        )
        .order_by(Job.first_seen_at.desc())
        .limit(limit)
    )
    if not include_closed:
        stmt = stmt.where(Job.closed_at.is_(None))

    return [
        JobWithCompany(
            id=job.id,
            title=job.title,
            url=job.url,
            location=job.location,
            posted_at=job.posted_at,
            first_seen_at=job.first_seen_at,
            closed_at=job.closed_at,
            company_id=company.id,
            company_name=company.name,
            company_slug=company.slug,
        )
        for job, company in db.execute(stmt)
    ]
