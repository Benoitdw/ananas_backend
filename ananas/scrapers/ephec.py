"""Haute Ecole EPHEC — Woluwe-Saint-Lambert. Module recrutement Odoo.

``recrutement.ephec.be/jobs`` est un site Odoo standard (module "Recrutement"
du site builder): chaque offre est une carte ``a[href^="/jobs/"]``, la fiche
n'a ni JSON-LD ni date de publication exposee. Les liens
``/jobs/candidature-spontanee-...`` ne sont pas des offres, ce sont des
formulaires de candidature spontanee permanents — a exclure.

Verifie le 2026-09-08: 2 offres (hors candidatures spontanees).
"""

from __future__ import annotations

import logging
from urllib.parse import urljoin

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import txt
from ananas.scrapers.registry import register

log = logging.getLogger(__name__)


@register
class EphecScraper(BaseScraper):
    key = "haute-ecole-ephec"
    label = "Haute Ecole EPHEC"
    careers_url = "https://recrutement.ephec.be/jobs"
    rate_limit = 0.3

    def fetch(self) -> list[JobPosting]:
        soup = self.get_soup(self.careers_url)
        links = {
            urljoin(self.careers_url, a["href"]): txt(a.select_one("h2, h3") or a)
            for a in soup.select("a[href^='/jobs/']")
            if "candidature-spontanee" not in a["href"]
        }
        postings = [
            posting
            for url, title in links.items()
            if title and (posting := self._to_posting(url, title))
        ]
        log.info("%s: %d offres", self.key, len(postings))
        return postings

    def _to_posting(self, url: str, title: str) -> JobPosting | None:
        try:
            soup = self.get_soup(url)
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: fiche %s illisible (%s)", self.key, url, exc)
            return None

        icon = soup.select_one("i[title='Adresse']")
        location = txt(icon.find_next_sibling("span")) if icon else ""
        body = soup.select_one("main")
        return JobPosting(
            title=title,
            url=url,
            location=location or None,
            description=txt(body)[:8000] if body else "",
            # Suffixe numerique de l'URL Odoo (ex. .../professeur-de-francais-45)
            external_id=url.rstrip("/").rsplit("-", 1)[-1],
        )
