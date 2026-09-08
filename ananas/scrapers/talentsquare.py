"""Base pour les sites carrieres heberges par TalentSquare (ex: Cap4HR).

TalentSquare rend la page carrieres en Angular ("phApp"-like: aucun HTML
serveur), mais l'app appelle une API JSON publique pour peupler le widget:

    GET https://<sous-domaine>.talentsquare.com/api/v2/careers_page/public
        ?slug=<sous-domaine>&public=true

``<sous-domaine>`` est le nom d'entreprise choisi par le client TalentSquare
(visible dans l'URL de la page carrieres). La reponse embarque toute la page
(sections "about", "team"...); seule la cle ``jobs.jobs`` nous interesse.

Verifie le 2026-09-08 (Cap4HR): 4 offres, un identifiant numerique stable par
offre.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, ClassVar

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import html_to_text

log = logging.getLogger(__name__)


class TalentSquareScraper(BaseScraper):
    """Sous-classer et definir ``key``, ``ts_slug`` (et ``careers_url``).

    Ne pas enregistrer cette classe: elle n'a pas de ``key``.
    """

    # Sous-domaine TalentSquare de l'entreprise, ex. "cap4hr"
    ts_slug: ClassVar[str] = ""
    rate_limit: ClassVar[float] = 0.4

    @property
    def api_url(self) -> str:
        return (
            f"https://{self.ts_slug}.talentsquare.com/api/v2/careers_page/public"
            f"?slug={self.ts_slug}&public=true"
        )

    def fetch(self) -> list[JobPosting]:
        data = self.get_json(self.api_url)
        jobs = ((data.get("jobs") or {}).get("jobs")) or []
        return [self._to_posting(j) for j in jobs]

    def _to_posting(self, job: dict[str, Any]) -> JobPosting:
        location = ", ".join(p for p in (job.get("city"), job.get("country")) if p) or None
        translations = job.get("translations") or {}
        # Les traductions sont keyees par langue ("fr", "en"...); on prend la
        # traduction primaire declaree par l'offre, a defaut la premiere venue.
        primary = job.get("primary_translation") or ""
        translation = translations.get(primary) or next(iter(translations.values()), {})
        description = translation.get("description") or job.get("short_description") or ""
        return JobPosting(
            title=(job.get("title") or "").strip(),
            url=job.get("absolute_url") or self.careers_url,
            location=location,
            description=html_to_text(description),
            posted_at=_as_date(job.get("published_at")),
            # Identifiant numerique interne TalentSquare: stable, survit a un
            # changement de titre ou de slug d'URL.
            external_id=str(job["id"]) if job.get("id") is not None else None,
        )


def _as_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None
