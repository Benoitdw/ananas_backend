"""Liaison d'un compte Ananas a une conversation Telegram.

Un bot Telegram ne peut pas ecrire a quelqu'un qui ne lui a jamais parle:
l'initiative doit venir de l'utilisateur. Et le token du bot ne doit jamais
lui etre communique — c'est un secret serveur partage par tous les comptes.

D'ou ce protocole:

1. le serveur tire un code a usage unique et construit
   ``https://t.me/<bot>?start=<code>`` ;
2. l'utilisateur ouvre ce lien et appuie sur "Demarrer" — Telegram envoie
   ``/start <code>`` au bot ;
3. le serveur, seul detenteur du token, lit ``getUpdates``, retrouve le code
   et enregistre le ``chat.id``.

L'utilisateur ne voit jamais le token, et n'a pas a chercher son identifiant.

**getUpdates est une ressource exclusive et partagee.** Chaque appel avec un
``offset`` confirme definitivement les mises a jour precedentes: elles ne
seront plus jamais rejouees. Deux requetes concurrentes se voleraient donc
leurs messages. D'ou le verrou, et le fait que chaque vidange confronte les
mises a jour a **tous** les codes en attente, pas seulement a celui de
l'appelant.
"""

from __future__ import annotations

import logging
import re
import secrets
import threading
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ananas.models import AppState, NotificationChannel, TelegramLinkCode, User
from ananas.notifiers.telegram import TelegramApiError, bot_username, get_updates

log = logging.getLogger(__name__)

# Alphabet sans caracteres ambigus (ni O/0, ni I/1/l): le code peut etre lu a
# voix haute ou recopie a la main depuis un autre appareil.
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8
TTL = timedelta(minutes=15)
OFFSET_KEY = "telegram_update_offset"

# Un seul appel getUpdates a la fois dans le process.
_lock = threading.Lock()


def _now() -> datetime:
    return datetime.now(UTC)


def new_code(db: Session, user: User) -> TelegramLinkCode:
    """Remplace tout code en attente pour cet utilisateur.

    Un seul code vivant par compte: sinon un code abandonne dans un onglet
    ouvert la veille pourrait lier une conversation a l'insu de l'utilisateur.
    """
    for stale in db.scalars(
        select(TelegramLinkCode).where(TelegramLinkCode.user_id == user.id)
    ):
        db.delete(stale)

    code = TelegramLinkCode(
        user_id=user.id,
        code="".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH)),
        expires_at=_now() + TTL,
    )
    db.add(code)
    db.commit()
    db.refresh(code)
    return code


def deep_link(code: str) -> str:
    """Lien qui ouvre la conversation avec le bot et prepare `/start <code>`."""
    return f"https://t.me/{bot_username()}?start={code}"


def _get_offset(db: Session) -> int | None:
    row = db.get(AppState, OFFSET_KEY)
    return int(row.value) if row and row.value else None


def _set_offset(db: Session, offset: int) -> None:
    row = db.get(AppState, OFFSET_KEY)
    if row is None:
        db.add(AppState(key=OFFSET_KEY, value=str(offset)))
    else:
        row.value = str(offset)


# "/start ABC123", "/start@MonBot ABC123", ou le code colle seul
_START = re.compile(r"^/start(?:@\w+)?\s+(\S+)$", re.I)


def _extract_code(text: str) -> str | None:
    text = (text or "").strip()
    if m := _START.match(text):
        return m.group(1).upper()
    # Repli: l'utilisateur a ouvert le bot sans passer par le lien et colle le
    # code a la main.
    if re.fullmatch(rf"[{ALPHABET}]{{{CODE_LENGTH}}}", text.upper()):
        return text.upper()
    return None


def drain_updates(db: Session) -> int:
    """Consomme les mises a jour en attente et resout les codes reconnus.

    Retourne le nombre de codes lies. Ne leve pas: un echec reseau doit
    laisser l'utilisateur reessayer, pas casser la page Parametres.
    """
    with _lock:
        try:
            updates = get_updates(offset=_get_offset(db))
        except TelegramApiError as exc:
            log.warning("getUpdates: %s", exc)
            return 0

        if not updates:
            return 0

        pending = {
            c.code: c
            for c in db.scalars(
                select(TelegramLinkCode).where(
                    TelegramLinkCode.chat_id.is_(None), TelegramLinkCode.expires_at > _now()
                )
            )
        }

        matched = 0
        highest = 0
        for update in updates:
            highest = max(highest, update.get("update_id", 0))
            message = update.get("message") or update.get("channel_post") or {}
            chat = message.get("chat") or {}
            code = _extract_code(message.get("text", ""))
            if code and chat.get("id") is not None and (entry := pending.pop(code, None)):
                entry.chat_id = str(chat["id"])
                matched += 1

        # +1: confirme tout ce lot aupres de Telegram, qui ne le rejouera plus.
        _set_offset(db, highest + 1)
        db.commit()
        return matched


def resolve(db: Session, user: User) -> NotificationChannel | None:
    """Etat de la liaison en cours. Cree le canal des que le code est reconnu."""
    drain_updates(db)

    code = db.scalar(
        select(TelegramLinkCode)
        .where(TelegramLinkCode.user_id == user.id)
        .order_by(TelegramLinkCode.created_at.desc())
    )
    if code is None or code.chat_id is None:
        return None

    channel = db.scalar(
        select(NotificationChannel).where(
            NotificationChannel.user_id == user.id, NotificationChannel.type == "telegram"
        )
    )
    if channel is None:
        channel = NotificationChannel(user_id=user.id, type="telegram", target=code.chat_id)
        db.add(channel)
    else:
        channel.target = code.chat_id
        channel.enabled = True

    # Le code a servi: on le retire pour qu'il ne puisse pas etre rejoue.
    db.delete(code)
    db.commit()
    db.refresh(channel)
    return channel


def purge_expired(db: Session) -> None:
    for stale in db.scalars(select(TelegramLinkCode).where(TelegramLinkCode.expires_at < _now())):
        db.delete(stale)
    db.commit()
