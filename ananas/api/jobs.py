"""Feed des offres — le pendant web de la notification quotidienne.

Les scores viennent de ``job_matches``, deja materialise: trier ou filtrer par
pertinence est un simple ORDER BY / WHERE, pas un calcul a la volee. C'est ce
qui permet a ``scope=all`` de rester bon marche: le score de chaque offre pour
l'utilisateur est deja calcule (``score_all_for_user``), qu'elle vienne d'une
entreprise suivie ou non.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ananas.api.home import get_home
from ananas.db import get_db
from ananas.distance import distance_from
from ananas.models import (
    Company,
    HiddenCompany,
    HiddenJob,
    Job,
    JobFeatures,
    JobMatch,
    SavedCompany,
    User,
    UserProfile,
)
from ananas.schemas import JobWithCompany, MessageOut
from ananas.security import get_current_user

router = APIRouter(prefix="/api/me/jobs", tags=["offres"])

# Plafond de securite quand le tri ou le filtre porte sur la distance: on doit
# alors mesurer plus d'offres que la page n'en affichera. Tres au-dessus du
# volume reel (quelques milliers d'offres ouvertes pour tout le repertoire),
# assez bas pour qu'une base qui derape ne fasse pas tomber l'API.
SCAN_LIMIT = 20_000


@router.get("", response_model=list[JobWithCompany])
def my_jobs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    include_closed: bool = Query(False, description="inclure les offres disparues du site"),
    include_hidden: bool = Query(False, description="inclure les offres que tu as ecartees"),
    relevant_only: bool = Query(False, description="seulement au-dessus de ton seuil"),
    max_km: float | None = Query(
        None, gt=0, description="entreprise a moins de N km de ton domicile"
    ),
    sort: str = Query("date", description="'date', 'score' ou 'distance'"),
    scope: str = Query(
        "saved", description="'saved' (par defaut, ta veille) ou 'all' (tout le repertoire scrape)"
    ),
    limit: int = Query(200, le=1000),
) -> list[JobWithCompany]:
    profile = db.get(UserProfile, user.id)
    threshold = profile.match_threshold if profile else 0
    home = get_home(db, user)
    point = home.point if home else None

    saved_ids = select(SavedCompany.company_id).where(SavedCompany.user_id == user.id)
    hidden_ids = select(HiddenJob.job_id).where(HiddenJob.user_id == user.id)
    muted_ids = select(HiddenCompany.company_id).where(HiddenCompany.user_id == user.id)
    stmt = (
        select(Job, Company, JobMatch, JobFeatures, Company.id.in_(saved_ids), Job.id.in_(hidden_ids))
        .join(Company, Company.id == Job.company_id)
        .outerjoin(JobMatch, (JobMatch.job_id == Job.id) & (JobMatch.user_id == user.id))
        .outerjoin(JobFeatures, JobFeatures.job_id == Job.id)
    )
    if scope != "all":
        stmt = stmt.where(Company.id.in_(saved_ids))
    # Une entreprise masquee sort du feed dans les deux scopes, et sans
    # echappatoire: `include_hidden` ne parle que des offres ecartees une par
    # une. Masquer la boite est une decision d'un autre ordre — on la respecte
    # jusqu'au bout, et on la defait depuis la fiche de l'entreprise.
    stmt = stmt.where(Company.id.not_in(muted_ids))
    if not include_closed:
        stmt = stmt.where(Job.closed_at.is_(None))
    if not include_hidden:
        stmt = stmt.where(Job.id.not_in(hidden_ids))
    if relevant_only:
        stmt = stmt.where(JobMatch.score >= threshold)

    # Les offres sans score (profil absent, extraction en attente) restent
    # visibles: elles passent en fin de tri plutot que de disparaitre.
    # Job.id en dernier: un meme scrape date des dizaines d'offres a la meme
    # seconde, sans ce departage la coupe a `limit` serait arbitraire.
    stmt = stmt.order_by(
        JobMatch.score.desc().nullslast() if sort == "score" else Job.first_seen_at.desc(),
        Job.id.desc(),
    )

    # La distance n'est pas une colonne SQL: rayon et tri par distance se font
    # en Python, donc apres coup. Couper a `limit` en base sortirait alors les
    # bonnes offres du lot avant meme de les avoir mesurees — on remonte plus
    # large dans ce cas, et on coupe a la fin.
    by_distance = max_km is not None or sort == "distance"
    stmt = stmt.limit(SCAN_LIMIT if by_distance else limit)

    rows = [
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
            company_saved=bool(saved),
            is_hidden=bool(hidden),
            distance_km=distance_from(point, company.lat, company.lon),
        )
        for job, company, match, features, saved, hidden in db.execute(stmt)
    ]

    if max_km is not None and point is not None:
        rows = [r for r in rows if r.distance_km is not None and r.distance_km <= max_km]
    if sort == "distance":
        rows.sort(key=lambda r: (r.distance_km is None, r.distance_km or 0.0))

    return rows[:limit]


@router.put("/{job_id}/hidden", response_model=MessageOut)
def hide_job(
    job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> MessageOut:
    """Ecarte une offre du feed. Idempotent: la cacher deux fois n'est pas une erreur."""
    if db.get(Job, job_id) is None:
        raise HTTPException(404, "Offre inconnue")

    if db.get(HiddenJob, {"user_id": user.id, "job_id": job_id}) is None:
        db.add(HiddenJob(user_id=user.id, job_id=job_id))
        db.commit()
    return MessageOut(detail="Offre ecartee")


@router.delete("/{job_id}/hidden", response_model=MessageOut)
def unhide_job(
    job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> MessageOut:
    existing = db.get(HiddenJob, {"user_id": user.id, "job_id": job_id})
    if existing is not None:
        db.delete(existing)
        db.commit()
    return MessageOut(detail="Offre reaffichee")
