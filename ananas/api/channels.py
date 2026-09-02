"""Canaux de notification.

La liaison Telegram passe par un lien profond a usage unique: l'utilisateur
appuie sur "Demarrer" dans le bot, et le serveur retrouve son ``chat.id``. Le
token du bot ne quitte jamais le serveur — voir ``ananas/telegram_link.py``.

Le bouton "Envoyer un test" reste ce qui rend la configuration verifiable:
sans lui, une conversation mal liee ne se manifeste que par l'absence
silencieuse de notification le lendemain.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ananas.db import get_db
from ananas.models import NotificationChannel, User
from ananas.notifiers.base import NotifierError
from ananas.notifiers.registry import available_types, get_notifier
from ananas.notifiers.telegram import TelegramApiError, bot_username
from ananas.schemas import (
    ChannelIn,
    ChannelOut,
    ChannelUpdate,
    MessageOut,
    TelegramLinkOut,
    TelegramLinkStatus,
)
from ananas.security import get_current_user
from ananas.telegram_link import deep_link, new_code, purge_expired, resolve

router = APIRouter(prefix="/api/me/channels", tags=["notifications"])


def _notifier_or_400(type_: str):
    notifier = get_notifier(type_)
    if notifier is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Transport '{type_}' inconnu. Disponibles: {', '.join(available_types())}",
        )
    return notifier


def _owned(db: Session, channel_id: int, user: User) -> NotificationChannel:
    channel = db.get(NotificationChannel, channel_id)
    if channel is None or channel.user_id != user.id:
        raise HTTPException(404, "Canal inconnu")
    return channel


@router.get("/types", response_model=list[dict])
def list_types() -> list[dict]:
    """Transports disponibles, avec leur etat de configuration serveur."""
    return [
        {
            "type": t,
            "label": get_notifier(t).label or t,
            "configured": get_notifier(t).is_configured(),
        }
        for t in available_types()
    ]


# ------------------------------------------------------- liaison Telegram


@router.post("/telegram/link", response_model=TelegramLinkOut)
def start_telegram_link(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> TelegramLinkOut:
    """Ouvre une liaison: renvoie un code a usage unique et son lien profond.

    Le code est valable 15 minutes et remplace tout code precedent du compte.
    """
    try:
        username = bot_username()
    except TelegramApiError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    purge_expired(db)
    code = new_code(db, user)
    return TelegramLinkOut(
        code=code.code,
        url=deep_link(code.code),
        bot_username=username,
        expires_at=code.expires_at,
    )


@router.get("/telegram/link", response_model=TelegramLinkStatus)
def poll_telegram_link(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> TelegramLinkStatus:
    """Interroge l'avancement. Appelee en boucle par la page Parametres.

    C'est cet appel qui consomme les mises a jour Telegram: il resout aussi
    les codes des autres utilisateurs en attente, faute de quoi une requete
    concurrente ferait disparaitre leur message.
    """
    channel = resolve(db, user)
    if channel is None:
        return TelegramLinkStatus(status="pending")
    return TelegramLinkStatus(status="linked", channel=ChannelOut.model_validate(channel))


@router.get("", response_model=list[ChannelOut])
def list_channels(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[NotificationChannel]:
    return list(
        db.scalars(
            select(NotificationChannel)
            .where(NotificationChannel.user_id == user.id)
            .order_by(NotificationChannel.id)
        )
    )


@router.post("", response_model=ChannelOut, status_code=status.HTTP_201_CREATED)
def create_channel(
    payload: ChannelIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> NotificationChannel:
    notifier = _notifier_or_400(payload.type)
    target = payload.target.strip()
    if not notifier.validate_target(target):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Identifiant invalide pour {notifier.label or payload.type}",
        )

    existing = db.scalar(
        select(NotificationChannel).where(
            NotificationChannel.user_id == user.id, NotificationChannel.type == payload.type
        )
    )
    # Un seul canal par transport: on met a jour plutot que de refuser, c'est
    # ce que fait naturellement le formulaire de la page Parametres.
    if existing is not None:
        existing.target = target
        existing.enabled = payload.enabled
        db.commit()
        db.refresh(existing)
        return existing

    channel = NotificationChannel(
        user_id=user.id, type=payload.type, target=target, enabled=payload.enabled
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return channel


@router.patch("/{channel_id}", response_model=ChannelOut)
def update_channel(
    channel_id: int,
    payload: ChannelUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotificationChannel:
    channel = _owned(db, channel_id, user)

    if payload.target is not None:
        notifier = _notifier_or_400(channel.type)
        target = payload.target.strip()
        if not notifier.validate_target(target):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Identifiant invalide")
        channel.target = target
    if payload.enabled is not None:
        channel.enabled = payload.enabled

    db.commit()
    db.refresh(channel)
    return channel


@router.delete("/{channel_id}", response_model=MessageOut)
def delete_channel(
    channel_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> MessageOut:
    db.delete(_owned(db, channel_id, user))
    db.commit()
    return MessageOut(detail="Canal supprime")


@router.post("/{channel_id}/test", response_model=MessageOut)
def test_channel(
    channel_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> MessageOut:
    channel = _owned(db, channel_id, user)
    notifier = _notifier_or_400(channel.type)
    try:
        notifier.send_test(channel.target)
    except NotifierError as exc:
        # 502: l'echec vient du service tiers ou d'une cible invalide,
        # pas d'une erreur de l'API.
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    return MessageOut(detail="Message de test envoye")
