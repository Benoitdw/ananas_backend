"""Notification par bot Telegram.

Un seul bot cote serveur (``TELEGRAM_BOT_TOKEN``), partage par tous les
utilisateurs. Chaque utilisateur ne fournit que son ``chat_id``, saisi dans la
page Parametres — c'est le "id conversation bot" a changer.

Pour obtenir son chat_id: parler une fois au bot, puis appeler
``https://api.telegram.org/bot<TOKEN>/getUpdates``. Le helper
``resolve_chat_ids()`` en bas de fichier fait exactement ca.
"""

from __future__ import annotations

import html
import logging
import re

import requests

from ananas.config import settings
from ananas.notifiers.base import BaseNotifier, Digest, NotifierError
from ananas.notifiers.registry import register

log = logging.getLogger(__name__)

API_ROOT = "https://api.telegram.org"
# Telegram refuse les messages de plus de 4096 caracteres
MAX_LENGTH = 4096


@register
class TelegramNotifier(BaseNotifier):
    type = "telegram"
    label = "Telegram"

    # --------------------------------------------------------------- contrat

    def is_configured(self) -> bool:
        return bool(settings.telegram_bot_token)

    def validate_target(self, target: str) -> bool:
        """Un chat_id est un entier, negatif pour les groupes et supergroupes."""
        return bool(re.fullmatch(r"-?\d{1,20}", target.strip()))

    def send(self, target: str, digest: Digest) -> None:
        self._post(target, self.render(digest))

    def send_test(self, target: str) -> None:
        self._post(
            target,
            "🍍 <b>Ananas</b> — message de test.\n"
            "Ce canal est bien configure: tu recevras ici les nouvelles offres "
            "des entreprises que tu as enregistrees.",
        )

    # ------------------------------------------------------------- rendu HTML

    def render(self, digest: Digest) -> str:
        n = digest.job_count
        plural = "s" if n > 1 else ""
        lines = [f"🍍 <b>{n} nouvelle{plural} offre{plural}</b>", ""]

        for company, jobs in digest.companies.items():
            lines.append(f"<b>{html.escape(company)}</b>")
            for job in jobs:
                title = html.escape(job.title)
                suffix = f" — <i>{html.escape(job.location)}</i>" if job.location else ""
                lines.append(f'  • <a href="{html.escape(job.url, quote=True)}">{title}</a>{suffix}')
            lines.append("")

        return self._truncate("\n".join(lines).strip())

    @staticmethod
    def _truncate(message: str) -> str:
        """Coupe proprement sur une fin de ligne si le message est trop long."""
        if len(message) <= MAX_LENGTH:
            return message
        notice = "\n\n… message tronque, voir la liste complete sur Ananas."
        cut = message[: MAX_LENGTH - len(notice)]
        return cut[: cut.rfind("\n")] + notice

    # ------------------------------------------------------------------ envoi

    def _post(self, chat_id: str, text: str) -> None:
        if not self.is_configured():
            raise NotifierError("TELEGRAM_BOT_TOKEN n'est pas configure cote serveur")

        url = f"{API_ROOT}/bot{settings.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            # Sans ca, Telegram colle un gros encart d'apercu sous le premier lien
            "disable_web_page_preview": True,
        }
        try:
            response = requests.post(url, json=payload, timeout=20)
        except requests.RequestException as exc:
            raise NotifierError(f"Telegram injoignable: {exc}") from exc

        if response.status_code != 200:
            # Le corps de reponse porte la vraie cause ("chat not found",
            # "bot was blocked by the user"...), on la remonte telle quelle.
            detail = _describe(response)
            raise NotifierError(f"Telegram a refuse l'envoi ({response.status_code}): {detail}")


def _describe(response: requests.Response) -> str:
    try:
        return response.json().get("description", response.text[:200])
    except ValueError:
        return response.text[:200]


def resolve_chat_ids(token: str | None = None) -> list[dict]:
    """Liste les conversations recentes du bot, pour retrouver un chat_id.

    Utilitaire de mise au point:
        python -c "from ananas.notifiers.telegram import resolve_chat_ids as r; print(r())"
    """
    token = token or settings.telegram_bot_token
    if not token:
        raise NotifierError("TELEGRAM_BOT_TOKEN absent")

    response = requests.get(f"{API_ROOT}/bot{token}/getUpdates", timeout=20)
    response.raise_for_status()

    chats = {}
    for update in response.json().get("result", []):
        chat = (update.get("message") or update.get("channel_post") or {}).get("chat")
        if chat:
            chats[chat["id"]] = {
                "chat_id": str(chat["id"]),
                "type": chat.get("type"),
                "name": chat.get("title") or chat.get("username") or chat.get("first_name", ""),
            }
    return list(chats.values())
