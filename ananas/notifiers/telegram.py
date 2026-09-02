"""Notification par bot Telegram.

Un seul bot cote serveur (``TELEGRAM_BOT_TOKEN``), partage par tous les
utilisateurs. Chaque utilisateur n'est identifie que par son ``chat_id``.

**Le token ne sort jamais du serveur.** C'est un secret partage: qui le
detient peut piloter le bot et ecrire a tous les autres comptes. La liaison
d'un compte passe donc par un lien profond a usage unique (voir
``ananas/api/channels.py``): un bot Telegram ne pouvant pas ecrire le premier,
c'est l'utilisateur qui envoie ``/start <code>``, et le serveur — seul
detenteur du token — lit le ``chat.id`` dans ``getUpdates``.
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
                bits = []
                if job.score is not None:
                    bits.append(f"{_badge(job.score)} {job.score}%")
                if job.location:
                    bits.append(f"<i>{html.escape(job.location)}</i>")
                suffix = f" — {' · '.join(bits)}" if bits else ""
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


# ------------------------------------------------------- API cote serveur
# Ces fonctions manipulent le token: elles ne doivent jamais etre exposees
# telles quelles a un client.


class TelegramApiError(RuntimeError):
    pass


def _api(method: str, **params):
    """Appel brut a l'API Telegram. Leve TelegramApiError en cas d'echec."""
    if not settings.telegram_bot_token:
        raise TelegramApiError("TELEGRAM_BOT_TOKEN n'est pas configure cote serveur")
    try:
        response = requests.get(
            f"{API_ROOT}/bot{settings.telegram_bot_token}/{method}", params=params, timeout=20
        )
    except requests.RequestException as exc:
        raise TelegramApiError(f"Telegram injoignable: {exc}") from exc

    if response.status_code != 200:
        raise TelegramApiError(f"Telegram a repondu {response.status_code}: {_describe(response)}")
    return response.json().get("result")


_bot_username: str | None = None


def bot_username() -> str:
    """Nom du bot, pour construire le lien profond. Mis en cache.

    Interroge ``getMe`` plutot que de dependre d'une variable d'environnement
    supplementaire: le token suffit a determiner de quel bot il s'agit.
    """
    global _bot_username
    if _bot_username is None:
        _bot_username = (_api("getMe") or {}).get("username", "")
    return _bot_username


def get_updates(offset: int | None = None, limit: int = 100) -> list[dict]:
    """Mises a jour en attente.

    ``offset`` confirme definitivement les mises a jour precedentes cote
    Telegram: il doit donc etre persiste, sinon on retraite ou on perd des
    messages. Timeout 0 (pas de long polling): l'appel est declenche par le
    navigateur qui interroge la page Parametres.
    """
    params = {"limit": limit, "timeout": 0}
    if offset is not None:
        params["offset"] = offset
    return _api("getUpdates", **params) or []


def _badge(score: int) -> str:
    """Un reperage visuel du score, lisible d'un coup d'oeil dans la notif."""
    if score >= 75:
        return "🟢"
    if score >= 55:
        return "🟡"
    return "⚪"


def _describe(response: requests.Response) -> str:
    try:
        return response.json().get("description", response.text[:200])
    except ValueError:
        return response.text[:200]


