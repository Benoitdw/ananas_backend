"""AstriVax — Leuven (Heverlee). WordPress, type de contenu ``vacancies``.

Le site publie ses offres comme un type de contenu WordPress expose par l'API
REST (``/wp-json/wp/v2/vacancies``): titre, lien, contenu HTML et date, avec
l'identifiant WordPress comme identifiant stable. La « candidature spontanee »
permanente est un document de ce type: ignoree.

Verifie le 2026-11-19: 0 offre (candidature spontanee seulement).
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import html_to_text
from ananas.scrapers.registry import register

log = logging.getLogger(__name__)


@register
class AstriVaxScraper(BaseScraper):
    key = "astrivax"
    label = "AstriVax"
    careers_url = "https://astrivax.com/vacancies/spontaneous-applications/"

    def fetch(self) -> list[JobPosting]:
        items = self.get_json(
            "https://astrivax.com/wp-json/wp/v2/vacancies", params={"per_page": 100}
        )
        postings = [
            self._to_posting(item)
            for item in items
            if "spontan" not in (item.get("slug") or "")
        ]
        log.info("%s: %d offres", self.key, len(postings))
        return postings

    def _to_posting(self, item: dict[str, Any]) -> JobPosting:
        return JobPosting(
            title=html_to_text((item.get("title") or {}).get("rendered") or ""),
            url=item.get("link") or self.careers_url,
            location="Leuven",
            description=html_to_text((item.get("content") or {}).get("rendered") or ""),
            posted_at=_as_date(item.get("date")),
            external_id=str(item.get("id") or "") or None,
        )


def _as_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None
