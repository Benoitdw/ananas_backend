"""Vue d'administration: les comptes, et de quoi cadrer le repertoire.

Deux principes tiennent ce module:

  - **Lecture seule sur les comptes.** L'administration voit qui utilise
    l'outil et ce qu'il en fait — nombre d'entreprises suivies, canal de
    notification configure, profil analyse — mais jamais le contenu: ni CV, ni
    aspirations, ni chat_id Telegram. Ces donnees n'aident pas a moderer un
    repertoire, et les exposer ferait de la page admin une cible.
  - **Le drapeau ne s'accorde pas par HTTP.** `is_admin` se pose uniquement par
    `python -m ananas.admin`, donc depuis le serveur. Aucune route ne promeut
    un compte, y compris celles-ci.

L'edition des fiches n'est pas ici mais dans `api/companies.py`: c'est la meme
route pour l'administration et pour l'utilisateur qui corrige sa propre
proposition (`PATCH /api/companies/{id}`), avec une seule regle d'acces —
inutile d'en ecrire deux versions qui divergeraient.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ananas.db import get_db
from ananas.models import (
    Company,
    Job,
    NotificationChannel,
    SavedCompany,
    User,
    UserProfile,
)
from ananas.schemas import AdminStatsOut, AdminUserOut
from ananas.scrapers.registry import load_scrapers
from ananas.security import get_current_admin

router = APIRouter(
    prefix="/api/admin",
    tags=["administration"],
    dependencies=[Depends(get_current_admin)],
)


def _counts(db: Session, column) -> dict[int, int]:
    """{user_id: n} pour une colonne qui reference un compte.

    La cle None (une fiche sans auteur) est ecartee: elle ne correspond a
    aucune ligne du tableau.
    """
    rows = db.execute(select(column, func.count()).group_by(column)).all()
    return {user_id: n for user_id, n in rows if user_id is not None}


@router.get("/users", response_model=list[AdminUserOut])
def list_users(db: Session = Depends(get_db)) -> list[AdminUserOut]:
    """Tous les comptes, du plus recent au plus ancien.

    Trois agregats en trois requetes plutot qu'un compteur par ligne: la page
    reste a quatre requetes quel que soit le nombre de comptes.
    """
    saved = _counts(db, SavedCompany.user_id)
    channels = _counts(db, NotificationChannel.user_id)
    submitted = _counts(db, Company.submitted_by_user_id)
    with_profile = set(db.scalars(select(UserProfile.user_id)))

    users = db.scalars(select(User).order_by(User.created_at.desc(), User.id.desc()))
    return [
        AdminUserOut(
            id=u.id,
            email=u.email,
            created_at=u.created_at,
            is_active=u.is_active,
            is_admin=u.is_admin,
            saved_companies=saved.get(u.id, 0),
            submitted_companies=submitted.get(u.id, 0),
            channels=channels.get(u.id, 0),
            has_profile=u.id in with_profile,
        )
        for u in users
    ]


@router.get("/stats", response_model=AdminStatsOut)
def stats(db: Session = Depends(get_db)) -> AdminStatsOut:
    """De quoi cadrer la page: volumes du repertoire et des comptes."""
    by_source = dict(
        db.execute(select(Company.source, func.count()).group_by(Company.source)).all()
    )
    return AdminStatsOut(
        users=db.scalar(select(func.count()).select_from(User)) or 0,
        companies=sum(by_source.values()),
        companies_by_source=by_source,
        user_submissions=db.scalar(
            select(func.count()).select_from(Company).where(Company.submitted_by_user_id.isnot(None))
        )
        or 0,
        jobs_open=db.scalar(select(func.count()).select_from(Job).where(Job.closed_at.is_(None)))
        or 0,
        scrapers=len(load_scrapers()),
    )
