"""Base pour les pages carrieres Beehire (``app.beehire.com/career/<slug>``).

La page est une application JavaScript, mais elle se peuple depuis une route
JSON publique:

    GET https://app.beehire.com/users/getPublicCampaigns/<slug>

Chaque « campagne » est une offre. Les textes sont indexes par langue
(``{"1": francais, "2": neerlandais, ...}``): on prend la langue declaree par
l'offre (``language``), a defaut la premiere renseignee. ``_id`` est un
ObjectId MongoDB, stable. La route ne publie aucune date; l'URL publique d'une
offre est son ``inviteLink``.

Verifie le 2026-11-19 (Hopitaux Iris Sud): 26 offres.
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import html_to_text

log = logging.getLogger(__name__)


class BeehireScraper(BaseScraper):
    """Sous-classer et definir ``key`` et ``beehire_slug``.

    Ne pas enregistrer cette classe: elle n'a pas de ``key``.
    """

    beehire_slug: ClassVar[str] = ""
    rate_limit: ClassVar[float] = 0.3

    def fetch(self) -> list[JobPosting]:
        data = self.get_json(f"https://app.beehire.com/users/getPublicCampaigns/{self.beehire_slug}")
        postings = [self._to_posting(c) for c in data.get("campaigns") or []]
        log.info("%s: %d offres", self.key, len(postings))
        return postings

    def _to_posting(self, campaign: dict[str, Any]) -> JobPosting:
        campaign_id = str(campaign.get("_id") or "")
        lang = str(campaign.get("language") or "")
        categories = campaign.get("jobCategories") or []
        return JobPosting(
            title=_text(campaign.get("title"), lang).strip(),
            url=campaign.get("inviteLink")
            or f"https://app.beehire.com/career/{self.beehire_slug}",
            location=_location(campaign),
            department=(categories[0].get("label") if categories else None) or None,
            description=html_to_text(_text(campaign.get("description"), lang)),
            external_id=campaign_id or None,
        )


def _text(value: Any, lang: str = "") -> str:
    """Texte d'un champ multilingue ``{"1": ..., "2": ...}``: la langue demandee,
    a defaut la premiere renseignee."""
    if isinstance(value, dict):
        if value.get(lang):
            return str(value[lang])
        for key in sorted(value, key=str):
            if value[key]:
                return str(value[key])
        return ""
    return str(value or "")


def _location(campaign: dict[str, Any]) -> str | None:
    loc = campaign.get("location") or {}
    if isinstance(loc, dict):
        return loc.get("city") or loc.get("name") or None
    return str(loc) or None
