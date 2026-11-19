"""DIAsource ImmunoAssays — Louvain-la-Neuve. Site propre, liste ``/job-offers``.

Chaque offre a une page ``/job-offers/<id>-<slug>``. Quand il n'y a pas de
poste ouvert, le site publie une fausse offre ``1219-no-open-positions``
(« There are currently no open positions »): ignoree. ``<id>`` est
l'identifiant du CMS, stable.

Verifie le 2026-11-19: 0 offre (seule la fausse offre « no open positions »).
"""

from __future__ import annotations

import logging
import re

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import txt
from ananas.scrapers.registry import register

log = logging.getLogger(__name__)

_OFFER = re.compile(r"/job-offers/(\d+)-([a-z0-9-]+)")


@register
class DiasourceScraper(BaseScraper):
    key = "diasource-immunoassays"
    label = "DIAsource ImmunoAssays"
    careers_url = "https://diasource-diagnostics.com/job-offers"

    def fetch(self) -> list[JobPosting]:
        soup = self.get_soup(self.careers_url)
        links: dict[str, str] = {}
        for a in soup.select("a[href*='/job-offers/']"):
            match = _OFFER.search(a["href"])
            if match and "no-open-position" not in match.group(2):
                links.setdefault(match.group(1), self.absolutize(a["href"]))
        postings = [self._detail(offer_id, url) for offer_id, url in links.items()]
        log.info("%s: %d offres", self.key, len(postings))
        return postings

    def _detail(self, offer_id: str, url: str) -> JobPosting:
        soup = self.get_soup(url)
        for node in soup(["script", "style", "nav", "header", "footer", "noscript"]):
            node.decompose()
        return JobPosting(
            title=txt(soup.find("h1")) or _OFFER.search(url).group(2).replace("-", " "),
            url=url,
            location="Louvain-la-Neuve",
            description=txt(soup.find("main") or soup.body)[:8000],
            external_id=offer_id,
        )
