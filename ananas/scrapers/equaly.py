"""Equaly — Woluwe-Saint-Lambert. Page carrieres statique (WordPress).

Pas d'ATS: la section "Open positions" de https://equaly.be/talent-careers/
liste chaque offre comme un bloc de texte libre (``h2.big_title`` sous
``.row.align-items-end.py-5``), titre et description completement melanges
dans le meme noeud — reflet d'une page composee a la main plutot que generee.
Une seule URL pour toute la page: pas de fiche individuelle, donc pas
d'``url`` distincte par offre.

Verifie le 2026-09-08: 1 offre (Research Scientist).
"""

from __future__ import annotations

import logging
import re

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import txt
from ananas.scrapers.registry import register

log = logging.getLogger(__name__)

# Longueur en dessous de laquelle un h2.big_title est un separateur decoratif
# vide plutot qu'une offre (ex. "Open positions" lui-meme).
_MIN_LEN = 20


@register
class EqualyScraper(BaseScraper):
    key = "equaly"
    label = "Equaly"
    careers_url = "https://equaly.be/talent-careers/index.html"
    rate_limit = 0.3

    def fetch(self) -> list[JobPosting]:
        soup = self.get_soup(self.careers_url)
        postings = []
        for h2 in soup.select(".row.align-items-end.py-5 h2.big_title"):
            description = txt(h2)
            if len(description) < _MIN_LEN:
                continue
            span = h2.select_one("span")
            title = txt(span) if span else description.split(".")[0]
            postings.append(
                JobPosting(
                    title=title,
                    url=self.careers_url,
                    location="Woluwe-Saint-Lambert",
                    description=description,
                    # Pas de fiche individuelle sur le site: seul le titre
                    # distingue une offre d'une autre.
                    external_id=re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or None,
                )
            )
        log.info("%s: %d offres", self.key, len(postings))
        return postings
