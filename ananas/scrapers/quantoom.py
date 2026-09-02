"""Quantoom Biosciences (Nivelles) — galaxie Univercells.

Site propre WordPress. La page ``/job-application/`` liste les offres
(``/job/<slug>/``) ; le corps est dans ``.entry-content``. La candidature
spontanee partage le meme gabarit d'URL — on l'exclut par slug.

Site unique → lieu constant (Nivelles).

Verifie le 2026-09-02 : 1 offre (Field & Operations Technician).
"""

from __future__ import annotations

import logging
from urllib.parse import urljoin

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import txt
from ananas.scrapers.registry import register

log = logging.getLogger(__name__)

_SKIP_SLUGS = {"spontaneous-application", "candidature-spontanee"}


@register
class QuantoomScraper(BaseScraper):
    key = "quantoom-biosciences"
    label = "Quantoom Biosciences"
    base_url = "https://quantoom.com"
    careers_url = "https://quantoom.com/job-application/"
    rate_limit = 0.3

    def fetch(self) -> list[JobPosting]:
        soup = self.get_soup(self.careers_url)
        links: dict[str, str] = {}
        for a in soup.select("a[href*='/job/']"):
            url = urljoin(self.base_url, a["href"]).split("?")[0]
            slug = url.rstrip("/").rsplit("/", 1)[-1]
            if slug in _SKIP_SLUGS:
                continue
            links.setdefault(url, txt(a))

        postings = [
            JobPosting(
                title=title or self._title(url),
                url=url,
                location="Nivelles",
                description=self._description(url),
                external_id=url.rstrip("/").rsplit("/", 1)[-1],
            )
            for url, title in links.items()
        ]
        log.info("%s: %d offres", self.key, len(postings))
        return postings

    def _page(self, url: str):
        try:
            return self.get_soup(url)
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: fiche %s illisible (%s)", self.key, url, exc)
            return None

    def _title(self, url: str) -> str:
        soup = self._page(url)
        node = soup.select_one("h1, h2, title") if soup else None
        return txt(node).split("•")[0].strip() if node else ""

    def _description(self, url: str) -> str:
        soup = self._page(url)
        body = soup.select_one(".entry-content, main, article") if soup else None
        return txt(body)[:8000] if body else ""
