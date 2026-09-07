"""Domicile de reference et perimetre de recherche.

Une adresse de domicile ne sert pas a livrer du courrier: elle sert a repondre
a « qu'est-ce qui est a moins de 30 km de chez moi ». D'ou trois choix:

  - rien n'est obligatoire — une ville seule place deja un cercle utile;
  - l'adresse n'est re-geocodee que si elle a change, pour qu'un simple
    deplacement du curseur de rayon ne coute pas une seconde d'attente
    Nominatim a chaque pixel;
  - la table est distincte de ``user_profiles``, qui est jetable (voir
    ``UserHome``).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ananas.db import get_db
from ananas.models import User, UserHome
from ananas.schemas import HomeIn, HomeOut, MessageOut
from ananas.security import get_current_user

router = APIRouter(prefix="/api/me/home", tags=["domicile"])


def get_home(db: Session, user: User) -> UserHome | None:
    """Le domicile d'un utilisateur, ou None. Point d'entree unique pour les
    autres routes qui annotent leurs reponses d'une distance."""
    return db.get(UserHome, user.id)


def compose_address(street: str, postal_code: str, city: str, country: str) -> str:
    """'Rue X 1, 1000 Bruxelles, Belgium' — meme forme que Company.address.

    Le pays seul ne fait pas une adresse: sans rue ni ville, on rend une chaine
    vide plutot qu'un « Belgium » que l'interface afficherait comme un domicile.
    """
    if not (street or postal_code or city):
        return ""
    return ", ".join(p for p in (street, f"{postal_code} {city}".strip(), country) if p)


@router.get("", response_model=HomeOut)
def read_home(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> HomeOut:
    """Renvoie un domicile vide plutot qu'un 404 quand il n'est pas renseigne:
    le front affiche le meme formulaire dans les deux cas."""
    home = get_home(db, user)
    return HomeOut.model_validate(home) if home else HomeOut()


@router.put("", response_model=HomeOut)
def save_home(
    payload: HomeIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> HomeOut:
    home = get_home(db, user)
    if home is None:
        home = UserHome(user_id=user.id)
        db.add(home)

    before = (home.street, home.postal_code, home.city, home.country)
    after = (payload.street, payload.postal_code, payload.city, payload.country)

    home.street, home.postal_code, home.city, home.country = after
    home.address = compose_address(*after)
    home.radius_km = payload.radius_km
    home.notify_within_radius = payload.notify_within_radius

    if after != before or home.lat is None:
        if any(after[:3]):
            # Import tardif: evite de payer l'import de requests au demarrage
            from ananas.geocoding import geocode

            home.lat, home.lon, home.geo_precision = geocode(
                street=payload.street,
                city=" ".join(p for p in (payload.postal_code, payload.city) if p),
                country=payload.country,
            )
        else:
            # Adresse effacee: on oublie aussi la position, sinon le cercle
            # resterait sur la carte sans rien pour l'expliquer.
            home.lat, home.lon, home.geo_precision = None, None, ""

    db.commit()
    db.refresh(home)
    return HomeOut.model_validate(home)


@router.delete("", response_model=MessageOut)
def delete_home(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> MessageOut:
    if home := get_home(db, user):
        db.delete(home)
        db.commit()
    return MessageOut(detail="Domicile supprime")
