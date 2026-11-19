"""Base pour les sites carrieres BambooHR (``<sous-domaine>.bamboohr.com``).

Le widget carrieres BambooHR consomme une API JSON publique, sans cle:

    GET https://<sous-domaine>.bamboohr.com/careers/list       -> offres ouvertes
    GET https://<sous-domaine>.bamboohr.com/careers/<id>/detail -> fiche

``<id>`` est l'identifiant numerique BambooHR de l'offre, stable.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, ClassVar

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import html_to_text

log = logging.getLogger(__name__)


class BambooHRScraper(BaseScraper):
    """Sous-classer et definir ``key`` et ``bamboo_slug``.

    Ne pas enregistrer cette classe: elle n'a pas de ``key``.
    """

    # Sous-domaine BambooHR, ex. "muna" pour muna.bamboohr.com
    bamboo_slug: ClassVar[str] = ""
    rate_limit: ClassVar[float] = 0.3

    @property
    def _root(self) -> str:
        return f"https://{self.bamboo_slug}.bamboohr.com/careers"

    def fetch(self) -> list[JobPosting]:
        data = self.get_json(f"{self._root}/list")
        postings = [self._to_posting(job) for job in data.get("result") or []]
        log.info("%s: %d offres", self.key, len(postings))
        return postings

    def _to_posting(self, job: dict[str, Any]) -> JobPosting:
        job_id = str(job.get("id") or "")
        description = ""
        try:
            detail = self.get_json(f"{self._root}/{job_id}/detail")
            opening = (detail.get("result") or {}).get("jobOpening") or {}
            description = html_to_text(opening.get("description") or "")
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: fiche %s illisible (%s)", self.key, job_id, exc)
        loc = job.get("location") or {}
        location = ", ".join(p for p in (loc.get("city"), loc.get("state")) if p) or None
        return JobPosting(
            title=(job.get("jobOpeningName") or "").strip(),
            url=f"{self._root}/{job_id}",
            location=location,
            department=job.get("departmentLabel") or None,
            description=description,
            posted_at=_as_date(job.get("datePosted")),
            external_id=job_id or None,
        )


def _as_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None
