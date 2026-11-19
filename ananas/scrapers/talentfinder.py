"""Base pour les sites carrieres TalentFinder (ATS belge, pages ``.aspx``).

TalentFinder heberge les offres sous ``<sous-domaine>.talentfinder.be`` ou sous
le domaine du client (``emploi.cspo.be``). Les listes sont rendues cote serveur:
chaque offre est un lien ``/<langue>/vacature/<id>/<slug>/``, ``<id>`` etant
l'identifiant TalentFinder, stable.

Selon le theme, la fiche publie un bloc schema.org ``JobPosting`` en JSON-LD
(Galactic) ou seulement le HTML (Clinique Saint-Pierre: ``h1`` + ``.jobdetail``).
On prend le JSON-LD quand il est la, le HTML sinon.

``galactic.py`` precede cette base et garde son propre code.
"""

from __future__ import annotations

import html as html_mod
import logging
import re
from datetime import date, datetime
from typing import Any, ClassVar
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import html_to_text, jsonld_job_posting, txt

log = logging.getLogger(__name__)

_VACATURE = re.compile(r"/vacature/(\d+)/")


class TalentFinderScraper(BaseScraper):
    """Sous-classer et definir ``key`` et ``careers_url`` (la page de liste).

    Ne pas enregistrer cette classe: elle n'a pas de ``key``.
    """

    # Lieu par defaut quand la fiche n'en declare pas (hopital mono-site...)
    default_location: ClassVar[str] = ""
    rate_limit: ClassVar[float] = 0.4

    def fetch(self) -> list[JobPosting]:
        soup = self.get_soup(self.careers_url)
        # url -> libelle du lien: le titre de repli quand la fiche n'a pas de
        # JSON-LD (le premier <h1> de certains themes est le logo).
        links: dict[str, str] = {}
        for a in soup.select("a[href*='/vacature/']"):
            if _VACATURE.search(a["href"]):
                url = urljoin(self.careers_url, a["href"])
                links[url] = links.get(url) or txt(a)
        postings = [p for url, label in sorted(links.items()) if (p := self._detail(url, label))]
        log.info("%s: %d offres", self.key, len(postings))
        return postings

    def _detail(self, url: str, label: str = "") -> JobPosting | None:
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            self.sleep()
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: fiche %s illisible (%s)", self.key, url, exc)
            return None

        job_id = _VACATURE.search(url).group(1)
        ld = jsonld_job_posting(response.text)
        if ld:
            return JobPosting(
                title=(ld.get("title") or "").strip(),
                url=url,
                location=_place(ld.get("jobLocation")) or self.default_location or None,
                description=html_to_text(html_mod.unescape(ld.get("description") or "")),
                posted_at=_as_date(ld.get("datePosted")),
                external_id=job_id,
            )

        soup = BeautifulSoup(response.text, "html.parser")
        body = soup.select_one(".jobdetail") or soup.select_one("main")
        heading = soup.select_one(".jobdetail h1, h1.greenH1")
        return JobPosting(
            title=label or txt(heading),
            url=url,
            location=self.default_location or None,
            description=txt(body)[:8000] if body else "",
            external_id=job_id,
        )


def _place(node: Any) -> str | None:
    node = node[0] if isinstance(node, list) and node else node
    address = (node or {}).get("address") or {}
    parts = [address.get("addressLocality"), address.get("addressCountry")]
    return ", ".join(p for p in parts if p) or None


def _as_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None
