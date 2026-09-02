"""Profil professionnel: CV, aspirations, et reglages de pertinence.

Enregistrer le profil declenche son extraction (~6 s) puis le rescoring de
toutes les offres ouvertes. C'est fait de facon synchrone: l'utilisateur vient
de coller son CV, il doit voir tout de suite ce qui en a ete compris — et
pouvoir le corriger si c'est faux.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ananas.ai.service import ai_ready, extract_user_profile
from ananas.db import get_db
from ananas.models import User, UserProfile
from ananas.schemas import MessageOut, ProfileIn, ProfileOut, ProfilePreferencesIn
from ananas.security import get_current_user

router = APIRouter(prefix="/api/me/profile", tags=["profil"])


def _get_or_create(db: Session, user: User) -> UserProfile:
    profile = db.get(UserProfile, user.id)
    if profile is None:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def _out(profile: UserProfile) -> ProfileOut:
    out = ProfileOut.model_validate(profile)
    out.ai_available = ai_ready()
    return out


@router.get("", response_model=ProfileOut)
def get_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ProfileOut:
    return _out(_get_or_create(db, user))


@router.put("", response_model=ProfileOut)
def save_profile(
    payload: ProfileIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ProfileOut:
    profile = _get_or_create(db, user)
    profile.cv_text = payload.cv_text.strip()
    profile.aspirations = payload.aspirations.strip()

    if not profile.cv_text and not profile.aspirations:
        # Profil vide: on efface l'extraction plutot que de garder des scores
        # calcules sur un profil qui n'existe plus.
        profile.data = None
        profile.status = None
        profile.error = None
        db.commit()
        return _out(profile)

    db.commit()
    extract_user_profile(db, profile)
    db.refresh(profile)
    return _out(profile)


@router.patch("/preferences", response_model=ProfileOut)
def update_preferences(
    payload: ProfilePreferencesIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProfileOut:
    profile = _get_or_create(db, user)
    if payload.match_threshold is not None:
        profile.match_threshold = payload.match_threshold
    if payload.notify_only_relevant is not None:
        profile.notify_only_relevant = payload.notify_only_relevant
    db.commit()
    db.refresh(profile)
    return _out(profile)


@router.delete("", response_model=MessageOut)
def delete_profile(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> MessageOut:
    if profile := db.get(UserProfile, user.id):
        db.delete(profile)
        db.commit()
    return MessageOut(detail="Profil supprime")
