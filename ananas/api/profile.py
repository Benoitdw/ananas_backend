"""Profil professionnel: CV, aspirations, et reglages de pertinence.

Enregistrer le profil declenche son extraction (~6 s) puis le rescoring de
toutes les offres ouvertes. C'est fait de facon synchrone: l'utilisateur vient
de coller son CV, il doit voir tout de suite ce qui en a ete compris — et
pouvoir le corriger si c'est faux.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ananas.ai.service import ai_ready, extract_user_profile
from ananas.cv_import import MAX_BYTES, CvImportError, read_cv
from ananas.db import get_db
from ananas.models import User, UserProfile
from ananas.schemas import (
    CvImportOut,
    MessageOut,
    ProfileIn,
    ProfileOut,
    ProfilePreferencesIn,
)
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


@router.post("/cv-file", response_model=CvImportOut)
def import_cv(
    file: UploadFile = File(...), user: User = Depends(get_current_user)
) -> CvImportOut:
    """Extrait le texte d'un CV en PDF. **N'enregistre rien.**

    Le texte est renvoye au formulaire, qui le place dans le champ CV pour que
    l'utilisateur le relise avant de lancer l'analyse: une extraction PDF
    melange souvent les colonnes, et analyser directement un texte non relu
    produirait un profil faux sans que personne s'en apercoive.
    """
    if file.content_type not in (None, "application/pdf", "application/octet-stream"):
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Seuls les fichiers PDF sont acceptes."
        )

    data = file.file.read(MAX_BYTES + 1)
    try:
        text, pages, method = read_cv(data)
    except CvImportError as exc:
        # 422: le fichier est arrive intact, c'est son contenu qui pose
        # probleme. Le message est destine a l'utilisateur.
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    return CvImportOut(
        text=text, pages=pages, method=method, filename=file.filename or "cv.pdf"
    )


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
