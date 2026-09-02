"""Inscription, connexion, deconnexion.

V1 sans envoi de mail: le compte est actif des sa creation, il n'y a ni
verification d'adresse ni reinitialisation de mot de passe.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ananas.db import get_db
from ananas.models import User
from ananas.schemas import LoginIn, MessageOut, RegisterIn, UserOut
from ananas.security import (
    clear_session_cookie,
    create_token,
    get_current_user,
    hash_password,
    normalize_email,
    set_session_cookie,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterIn, response: Response, db: Session = Depends(get_db)) -> User:
    email = normalize_email(payload.email)
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Un compte existe deja avec cet email")

    user = User(email=email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    # On connecte directement: pas d'ecran "verifiez vos mails" a franchir
    set_session_cookie(response, create_token(user))
    return user


@router.post("/login", response_model=UserOut)
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)) -> User:
    user = db.scalar(select(User).where(User.email == normalize_email(payload.email)))
    # Message identique dans les deux cas: ne pas reveler quels emails ont un compte
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email ou mot de passe incorrect")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Compte desactive")

    set_session_cookie(response, create_token(user))
    return user


@router.post("/logout", response_model=MessageOut)
def logout(response: Response) -> MessageOut:
    clear_session_cookie(response)
    return MessageOut(detail="Deconnecte")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
