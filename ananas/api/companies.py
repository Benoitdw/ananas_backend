"""Repertoire d'entreprises: ce qui peuple la carte, la fiche de detail, et le
formulaire de proposition.

Deux provenances cohabitent dans la meme table: les 81 partenaires importes du
repertoire BioWin (`source='biowin'`) et celles proposees par les utilisateurs
(`source='from_user'`). Une entreprise proposee est une entreprise a part
entiere — visible, filtrable et enregistrable par tout le monde.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ananas.db import get_db
from ananas.models import (
    SOURCE_USER,
    Company,
    Job,
    JobFeatures,
    JobMatch,
    SavedCompany,
    User,
    UserProfile,
)
from ananas.schemas import (
    CompanyDetail,
    CompanyFacets,
    CompanyListItem,
    CompanySubmitIn,
    JobOut,
)
from ananas.scrapers.registry import get_scraper
from ananas.security import get_current_user, get_current_user_optional
from ananas.seed import slugify, unique_slug

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


def _item(company: Company, saved: set[int], counts: dict[int, int]) -> CompanyListItem:
    return CompanyListItem(
        id=company.id,
        slug=company.slug,
        name=company.name,
        type=company.type,
        core_business=company.core_business,
        tags=company.tags,
        source=company.source,
        city=company.city,
        lat=company.lat,
        lon=company.lon,
        geo_precision=company.geo_precision,
        is_saved=company.id in saved,
        has_scraper=bool(company.scraper_key and get_scraper(company.scraper_key)),
        open_jobs=counts.get(company.id, 0),
    )


@router.get("", response_model=list[CompanyListItem])
def list_companies(
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
    q: str | None = Query(None, description="recherche libre: nom, ville, tag, resume"),
    type: str | None = Query(None),
    tag: str | None = Query(None, description="un tag, BioWin ou utilisateur"),
    core_business: str | None = Query(None, deprecated=True, description="alias de `tag`"),
    source: str | None = Query(None, description="'biowin' ou 'from_user'"),
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
                Company.tags.ilike(pattern),
                Company.baseline.ilike(pattern),
                Company.description.ilike(pattern),
            )
        )
    if type:
        stmt = stmt.where(Company.type == type)
    if source:
        stmt = stmt.where(Company.source == source)

    # Un seul filtre pour les deux colonnes: les tags utilisateur et les
    # secteurs BioWin partagent le meme vocabulaire cote interface.
    if wanted := (tag or core_business):
        needle = f"%{wanted}%"
        stmt = stmt.where(or_(Company.core_business.ilike(needle), Company.tags.ilike(needle)))

    saved = _saved_ids(db, user)
    if saved_only:
        if not saved:
            return []
        stmt = stmt.where(Company.id.in_(saved))

    counts = _open_job_counts(db)
    return [_item(c, saved, counts) for c in db.scalars(stmt)]


@router.get("/facets", response_model=CompanyFacets)
def facets(db: Session = Depends(get_db)) -> CompanyFacets:
    """Valeurs distinctes pour alimenter les filtres et l'autocompletion du
    formulaire de proposition."""
    types = sorted({t for t in db.scalars(select(Company.type).distinct()) if t})

    # Les deux colonnes stockent plusieurs valeurs separees par des virgules;
    # l'interface veut la liste a plat.
    tags: set[str] = set()
    for column in (Company.core_business, Company.tags):
        for raw in db.scalars(select(column).distinct()):
            tags.update(part.strip() for part in (raw or "").split(",") if part.strip())

    ordered = sorted(tags, key=str.casefold)
    return CompanyFacets(types=types, tags=ordered, core_businesses=ordered)


def _canonical_tags(db: Session, tags: list[str]) -> list[str]:
    """Reutilise l'orthographe des tags deja presents dans le repertoire.

    La normalisation du schema met les mots en capitales initiales, ce qui
    transformerait "Administrative & Office support" en "... Support" et
    creerait un quasi-doublon dans le filtre. Un tag qui existe deja, a la
    casse pres, doit garder son orthographe d'origine — c'est toute la valeur
    d'un vocabulaire partage.
    """
    existing: dict[str, str] = {}
    for column in (Company.core_business, Company.tags):
        for raw in db.scalars(select(column).distinct()):
            for part in (raw or "").split(","):
                if part := part.strip():
                    existing.setdefault(part.casefold(), part)

    return list(dict.fromkeys(existing.get(t.casefold(), t) for t in tags))


@router.post("", response_model=CompanyDetail, status_code=status.HTTP_201_CREATED)
def submit_company(
    payload: CompanySubmitIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CompanyDetail:
    """Propose une entreprise absente du repertoire.

    L'adresse est geocodee a la volee (Nominatim, ~1 s) pour que l'entreprise
    apparaisse immediatement sur la carte des autres utilisateurs. Le geocodage
    sait degrader: une ville suffit, et a defaut le nom seul est tente.
    """
    if existing := _find_duplicate(db, payload):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {
                "detail": f"« {existing.name} » est deja dans le repertoire.",
                "company_id": existing.id,
                "company_name": existing.name,
            },
        )

    # Import tardif: evite de payer l'import de requests au demarrage de l'API
    from ananas.geocoding import geocode

    lat, lon, precision = geocode(
        street=payload.street,
        city=" ".join(p for p in (payload.postal_code, payload.city) if p),
        country=payload.country,
        name=payload.name,
    )

    taken = set(db.scalars(select(Company.slug)))
    company = Company(
        slug=unique_slug(slugify(payload.name), taken),
        name=payload.name,
        source=SOURCE_USER,
        submitted_by_user_id=user.id,
        type=payload.type,
        tags=", ".join(_canonical_tags(db, payload.tags)),
        baseline=payload.baseline,
        description=payload.description,
        street=payload.street,
        postal_code=payload.postal_code,
        city=" ".join(p for p in (payload.postal_code, payload.city) if p),
        country=payload.country,
        address=", ".join(
            p for p in (payload.street, f"{payload.postal_code} {payload.city}".strip(), payload.country) if p
        ),
        lat=lat,
        lon=lon,
        geo_precision=precision,
        website=payload.website,
        email=payload.email,
        phone=payload.phone,
        linkedin=payload.linkedin,
        careers_url=payload.careers_url or None,
    )
    db.add(company)
    db.commit()
    db.refresh(company)

    # Enregistrer dans la foulee: on propose surtout une entreprise qu'on veut
    # soi-meme suivre, et cela evite un aller-retour vers la carte.
    if payload.save:
        db.add(SavedCompany(user_id=user.id, company_id=company.id))
        db.commit()

    return _detail(db, company, user)


def _find_duplicate(db: Session, payload: CompanySubmitIn) -> Company | None:
    """Evite les doublons dans un repertoire partage.

    Deux signaux: le slug du nom, et le domaine du site web — deux personnes
    ecrivent rarement le nom de la meme facon, mais pointent le meme domaine.
    """
    if existing := db.scalar(select(Company).where(Company.slug == slugify(payload.name))):
        return existing

    if domain := _domain(payload.website):
        for candidate in db.scalars(select(Company).where(Company.website != "")):
            if _domain(candidate.website) == domain:
                return candidate
    return None


def _domain(url: str) -> str:
    """Domaine nu, sans 'www.' ni casse, pour comparer deux sites."""
    if not url:
        return ""
    host = urlsplit(url if "//" in url else f"//{url}").netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _detail(db: Session, company: Company, user: User | None) -> CompanyDetail:
    """Les offres portent leur score quand l'utilisateur a un profil: c'est ce
    qui permet de n'afficher que les offres pertinentes d'une entreprise."""
    stmt = (
        select(Job, JobMatch, JobFeatures)
        .outerjoin(
            JobMatch,
            (JobMatch.job_id == Job.id) & (JobMatch.user_id == (user.id if user else 0)),
        )
        .outerjoin(JobFeatures, JobFeatures.job_id == Job.id)
        .where(Job.company_id == company.id, Job.closed_at.is_(None))
        .order_by(JobMatch.score.desc().nullslast(), Job.first_seen_at.desc())
    )

    jobs: list[JobOut] = []
    for job, match, features in db.execute(stmt):
        out = JobOut.model_validate(job)
        out.match_score = match.score if match else None
        out.match_reasons = (match.reasons if match else []) or []
        out.summary = features.summary if features else None
        jobs.append(out)

    detail = CompanyDetail.model_validate(company)
    detail.is_saved = company.id in _saved_ids(db, user)
    detail.jobs = jobs
    detail.submitted_by_email = company.submitted_by.email if company.submitted_by else None
    profile = db.get(UserProfile, user.id) if user else None
    detail.match_threshold = profile.match_threshold if profile else None
    return detail


@router.get("/{company_id}", response_model=CompanyDetail)
def get_company(
    company_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
) -> CompanyDetail:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(404, "Entreprise inconnue")
    return _detail(db, company, user)
