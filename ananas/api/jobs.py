"""Feed des offres — le pendant web de la notification quotidienne.

Les scores viennent de ``job_matches``, deja materialise: trier ou filtrer par
pertinence est un simple ORDER BY / WHERE, pas un calcul a la volee.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ananas.db import get_db
from ananas.models import Company, Job, JobFeatures, JobMatch, SavedCompany, User, UserProfile
from ananas.schemas import JobWithCompany
from ananas.security import get_current_user

router = APIRouter(prefix="/api/me/jobs", tags=["offres"])


@router.get("", response_model=list[JobWithCompany])
def my_jobs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    include_closed: bool = Query(False, description="inclure les offres disparues du site"),
    relevant_only: bool = Query(False, description="seulement au-dessus de ton seuil"),
    sort: str = Query("date", description="'date' ou 'score'"),
    limit: int = Query(200, le=1000),
) -> list[JobWithCompany]:
    profile = db.get(UserProfile, user.id)
    threshold = profile.match_threshold if profile else 0

    stmt = (
        select(Job, Company, JobMatch, JobFeatures)
        .join(Company, Company.id == Job.company_id)
        .join(
            SavedCompany,
            (SavedCompany.company_id == Company.id) & (SavedCompany.user_id == user.id),
        )
        .outerjoin(JobMatch, (JobMatch.job_id == Job.id) & (JobMatch.user_id == user.id))
        .outerjoin(JobFeatures, JobFeatures.job_id == Job.id)
        .limit(limit)
    )
    if not include_closed:
        stmt = stmt.where(Job.closed_at.is_(None))
    if relevant_only:
        stmt = stmt.where(JobMatch.score >= threshold)

    # Les offres sans score (profil absent, extraction en attente) restent
    # visibles: elles passent en fin de tri plutot que de disparaitre.
    stmt = stmt.order_by(
        JobMatch.score.desc().nullslast() if sort == "score" else Job.first_seen_at.desc()
    )

    return [
        JobWithCompany(
            id=job.id,
            title=job.title,
            url=job.url,
            location=job.location,
            department=job.department,
            posted_at=job.posted_at,
            first_seen_at=job.first_seen_at,
            closed_at=job.closed_at,
            match_score=match.score if match else None,
            match_reasons=(match.reasons if match else []) or [],
            summary=features.summary if features else None,
            company_id=company.id,
            company_name=company.name,
            company_slug=company.slug,
        )
        for job, company, match, features in db.execute(stmt)
    ]
