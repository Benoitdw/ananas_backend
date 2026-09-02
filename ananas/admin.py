"""Cree ou met a jour le compte d'administration, depuis le .env.

    python -m ananas.admin [--email ...] [--password ...] [--revoke email]

Deliberement une commande et non une route: `is_admin` ne peut etre leve par
aucune requete HTTP. Une elevation de privilege demande donc un acces au
serveur, pas une faille dans le formulaire d'inscription.

Idempotent — le compte est cree s'il n'existe pas, promu s'il existe, et son
mot de passe est reecrit a chaque passage. C'est ce qui permet de changer le
mot de passe admin en editant le .env puis en relancant la commande.
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import select

from ananas.config import settings
from ananas.db import session_scope
from ananas.models import User
from ananas.security import hash_password, normalize_email

MIN_PASSWORD = 8


def grant(email: str, password: str) -> tuple[User, bool]:
    """Retourne (utilisateur, cree)."""
    email = normalize_email(email)
    if len(password) < MIN_PASSWORD:
        raise SystemExit(f"Mot de passe trop court ({MIN_PASSWORD} caracteres minimum)")

    with session_scope() as db:
        user = db.scalar(select(User).where(User.email == email))
        created = user is None
        if user is None:
            user = User(email=email, password_hash=hash_password(password))
            db.add(user)
        else:
            user.password_hash = hash_password(password)
        user.is_admin = True
        user.is_active = True
        db.flush()
        db.expunge_all()
        return user, created


def revoke(email: str) -> bool:
    with session_scope() as db:
        user = db.scalar(select(User).where(User.email == normalize_email(email)))
        if user is None:
            return False
        user.is_admin = False
        return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ananas-admin", description=__doc__)
    parser.add_argument("--email", default=settings.admin_email)
    parser.add_argument("--password", default=settings.admin_password)
    parser.add_argument("--revoke", metavar="EMAIL", help="retire le droit d'administration")
    args = parser.parse_args(argv)

    if args.revoke:
        if revoke(args.revoke):
            print(f"{normalize_email(args.revoke)} n'est plus administrateur")
            return 0
        print(f"Aucun compte pour {args.revoke}", file=sys.stderr)
        return 1

    if not args.email or not args.password:
        raise SystemExit(
            "Renseigne ADMIN_EMAIL et ADMIN_PASSWORD dans le .env, "
            "ou passe --email et --password."
        )

    user, created = grant(args.email, args.password)
    print(f"{user.email} {'cree' if created else 'mis a jour'} — administrateur")
    return 0


if __name__ == "__main__":
    sys.exit(main())
