"""Novadip Biosciences — Mont-Saint-Guibert.

Site propre (WordPress). La page ``/careers/`` liste les offres ouvertes sous
forme de liens ``/open-positions/<slug>/`` ; chaque fiche porte le texte
complet dans ``.et_pb_post_content``. Site unique → lieu constant.

Verifie le 2026-09-02 : 1 offre (Quality Assurance Manager).
"""

from __future__ import annotations

import logging
from urllib.parse import urljoin

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import txt
from ananas.scrapers.registry import register

log = logging.getLogger(__name__)


@register
class NovadipScraper(BaseScraper):
    key = "novadip-biosciences"
    label = "Novadip Biosciences"
    careers_url = "https://novadip.com/careers/"
    rate_limit = 0.3

    def fetch(self) -> list[JobPosting]:
        soup = self.get_soup(self.careers_url)
        links = {
            urljoin(self.careers_url, a["href"]): txt(a)
            for a in soup.select("a[href*='/open-positions/']")
            if txt(a).lower() not in ("", "read more", "en savoir plus", "apply")
        }
        postings = [
            JobPosting(
                title=title,
                url=url,
                location="Mont-Saint-Guibert",
                description=self._description(url),
                # slug de l'URL : identifiant stable faute d'id expose par le site
                external_id=url.rstrip("/").rsplit("/", 1)[-1],
            )
            for url, title in links.items()
        ]
        log.info("%s: %d offres", self.key, len(postings))
        return postings

    def _description(self, url: str) -> str:
        try:
            soup = self.get_soup(url)
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: fiche %s illisible (%s)", self.key, url, exc)
            return ""
        body = soup.select_one(".et_pb_post_content, article, main")
        return txt(body)[:8000] if body else ""
