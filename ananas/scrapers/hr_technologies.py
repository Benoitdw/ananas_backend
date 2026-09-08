"""Base pour les sites carrieres HR-Technologies (utilise par Sciensano).

Le site n'est qu'une coquille Vue.js (``jobs.<entreprise>.be/front/<locale>``)
sans HTML serveur; les offres viennent d'une API JSON publique commune a tous
les clients de la plateforme:

    GET https://api.hr-technologies.com/v1/vacancies
    Header: X-Client-UUID: <uuid propre a l'entreprise>

``client_uuid`` est lu dans la meta ``<meta name="client-uuid">`` de la page
carrieres (visible sans authentification). Reponse paginee au sens JSON:API
(``data`` / ``links`` / ``meta``), mais chaque page fait 20 offres et
Sciensano n'en a que quelques-unes — pas de pagination geree ici tant qu'aucun
client suivi n'en a besoin.

Verifie le 2026-09-08 (Sciensano): 7 offres, description complete par offre.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, ClassVar

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import html_to_text

log = logging.getLogger(__name__)

API_BASE = "https://api.hr-technologies.com/v1"


class HRTechnologiesScraper(BaseScraper):
    """Sous-classer et definir ``key``, ``client_uuid`` (et ``front_url``).

    Ne pas enregistrer cette classe: elle n'a pas de ``key``.
    """

    # UUID client HR-Technologies, lu dans <meta name="client-uuid"> de la
    # page carrieres publique.
    client_uuid: ClassVar[str] = ""
    # Racine du site vitrine, ex. "https://jobs.sciensano.be/front/fr"
    front_url: ClassVar[str] = ""
    rate_limit: ClassVar[float] = 0.4

    def fetch(self) -> list[JobPosting]:
        data = self.get_json(f"{API_BASE}/vacancies", headers={"X-Client-UUID": self.client_uuid})
        return [self._to_posting(v) for v in data.get("data") or []]

    def _to_posting(self, v: dict[str, Any]) -> JobPosting:
        location = v.get("location") or ", ".join(v.get("regions") or [])
        return JobPosting(
            title=(v.get("title") or "").strip(),
            # Le site ne publie pas d'URL de fiche stable connue (route SPA
            # non confirmee) : on renvoie vers le site vitrine, le slug
            # identifie l'offre de facon unique via external_id.
            url=f"{self.front_url.rstrip('/')}/vacancy/{v['slug']}"
            if v.get("slug")
            else self.careers_url,
            location=location or None,
            description=html_to_text(v.get("description") or v.get("short_description") or ""),
            posted_at=_as_date(v.get("created_at")),
            external_id=str(v["id"]) if v.get("id") is not None else None,
        )


def _as_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace(" ", "T")).date()
    except ValueError:
        return None
