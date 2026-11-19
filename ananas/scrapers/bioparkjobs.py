"""Base pour les entreprises qui publient sur biopark.jobs (BioPark Charleroi).

``www.biopark.jobs`` est le jobboard commun des entreprises du BioPark de
Gosselies, motorise par TalentSquare. Plusieurs petites biotechs n'ont pas
d'autre page d'offres: leur site renvoie vers leur fiche employeur
(``/en/company/<id>/<slug>``).

La page ``/en/recent-jobs`` est rendue cote serveur et liste toutes les offres
en cours sous la forme ``/en/job/<employeur>/<id>/<slug>``. On filtre sur le
segment ``<employeur>`` (``bp_employer``), puis on lit chaque fiche: elle
publie un gabarit JSON-LD *non interprete* (du code PHP brut, inexploitable),
d'ou la lecture du texte de la page. ``<id>`` est l'identifiant TalentSquare de
l'offre, stable.
"""

from __future__ import annotations

import logging
import re
from typing import ClassVar

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import txt

log = logging.getLogger(__name__)

ROOT = "https://www.biopark.jobs"
_JOB = re.compile(r"/en/job/([^/]+)/(\d+)/")


class BioparkJobsScraper(BaseScraper):
    """Sous-classer et definir ``key`` et ``bp_employer``.

    Ne pas enregistrer cette classe: elle n'a pas de ``key``.
    """

    # Segment employeur des URL d'offres, ex. "bioxodes"
    bp_employer: ClassVar[str] = ""
    max_pages: ClassVar[int] = 10
    rate_limit: ClassVar[float] = 0.4

    def fetch(self) -> list[JobPosting]:
        found: dict[str, tuple[str, str]] = {}
        for page in range(1, self.max_pages + 1):
            soup = self.get_soup(f"{ROOT}/en/recent-jobs?page={page}")
            new = 0
            for a in soup.select("a[href*='/en/job/']"):
                match = _JOB.search(a["href"])
                if not match or match.group(2) in found:
                    continue
                new += 1
                if match.group(1) == self.bp_employer:
                    found[match.group(2)] = (a["href"], txt(a.select_one("h3")) or txt(a))
            if not new:
                break

        postings = [self._detail(job_id, url, title) for job_id, (url, title) in found.items()]
        log.info("%s: %d offres", self.key, len(postings))
        return postings

    def _detail(self, job_id: str, url: str, title: str) -> JobPosting:
        description = ""
        try:
            soup = self.get_soup(url)
            for node in soup(["script", "style", "nav", "header", "footer", "noscript"]):
                node.decompose()
            body = soup.find("main") or soup.body
            description = txt(body)[:8000]
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: fiche %s illisible (%s)", self.key, url, exc)
        return JobPosting(title=title, url=url, description=description, external_id=job_id)
