"""Authentification: hash de mot de passe, JWT, dependance FastAPI.

Choix v1 assumes: pas d'envoi de mail, donc pas de verification d'adresse ni
de reinitialisation de mot de passe — un compte est actif des sa creation.
Le token vit dans un cookie httpOnly pour qu'un XSS cote front ne puisse pas
le lire.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, Request, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from ananas.config import settings
from ananas.db import get_db
from ananas.models import User

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_token(user: User) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_expire_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None


def set_session_cookie(response, token: str) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.jwt_expire_days * 24 * 3600,
        path="/",
    )


def clear_session_cookie(response) -> None:
    response.delete_cookie(key=settings.cookie_name, path="/")


def get_current_user_optional(
    request: Request, db: Session = Depends(get_db)
) -> User | None:
    """Utilisateur courant, ou None. Pour les routes publiques qui s'enrichissent
    quand on est connecte (la carte, qui marque les favoris)."""
    token = request.cookies.get(settings.cookie_name)
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    user = db.get(User, int(payload["sub"]))
    return user if user and user.is_active else None


def get_current_user(user: User | None = Depends(get_current_user_optional)) -> User:
    """Utilisateur courant obligatoire."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentification requise"
        )
    return user
