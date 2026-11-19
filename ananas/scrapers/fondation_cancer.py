"""Fondation contre le Cancer — Bruxelles. Offres CVWarehouse (``cvw.io``).

``cancer.be/jobs`` liste des cartes ``.job-card`` dont le lien pointe vers
``stichtingtegenkanker.cvw.io/?job=<id>``. ``<id>`` est l'identifiant
CVWarehouse, stable. La carte « Candidature spontanee » est ignoree. La fiche
CVWarehouse est rendue cote serveur: on en prend le texte.

Verifie le 2026-11-19: 2 offres (hors candidature spontanee).
"""

from __future__ import annotations

import logging
import re

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import txt
from ananas.scrapers.registry import register

log = logging.getLogger(__name__)

_JOB = re.compile(r"[?&]job=(\d+)")


@register
class FondationContreLeCancerScraper(BaseScraper):
    key = "fondation-contre-le-cancer"
    label = "Fondation contre le Cancer"
    careers_url = "https://cancer.be/jobs/"

    def fetch(self) -> list[JobPosting]:
        soup = self.get_soup(self.careers_url)
        postings: list[JobPosting] = []
        for card in soup.select(".job-card"):
            title = txt(card.select_one(".job-card__title"))
            link = card.select_one("a[href*='cvw.io']")
            match = _JOB.search(link["href"]) if link else None
            if not match or not title or "spontan" in title.casefold():
                continue
            postings.append(self._detail(link["href"], match.group(1), title))
        log.info("%s: %d offres", self.key, len(postings))
        return postings

    def _detail(self, url: str, job_id: str, title: str) -> JobPosting:
        description = ""
        try:
            soup = self.get_soup(url)
            for node in soup(["script", "style", "noscript", "nav", "header", "footer"]):
                node.decompose()
            description = txt(soup.body)[:8000]
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: fiche %s illisible (%s)", self.key, url, exc)
        return JobPosting(
            title=title,
            url=url,
            location="Bruxelles",
            description=description,
            external_id=job_id,
        )
