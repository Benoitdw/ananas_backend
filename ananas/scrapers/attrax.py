"""Base pour les sites carrieres Attrax (le CDN se trahit dans les URL:
``attraxcdnprod1...``). AbbVie l'utilise; d'autres grands groupes aussi.

Deux pages a lire, pour deux raisons differentes:

1. **La liste** ne rend que des vignettes (``attrax-vacancy-tile``): titre,
   lieu, quelques options — jamais l'annonce complete. Elle sert uniquement a
   trouver les URL des offres.
2. **La fiche** embarque un bloc ``<script type="application/ld+json">`` au
   format schema.org ``JobPosting``: titre, lieu, description complete, date
   de publication et un identifiant stable, tout au meme endroit et dans un
   vocabulaire fixe par la specification — bien plus robuste que des classes
   CSS maison, qui changent a chaque refonte du theme Attrax.

Le filtre pays (``li=BE``) est un filtre exact, pas une recherche de
proximite: contrairement a Phenom (voir ``phenom.py``), pas de piege ici — un
poste listé pour ``li=BE`` est bien en Belgique, aucun post-filtrage requis.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime
from typing import Any, ClassVar

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import html_to_text

log = logging.getLogger(__name__)

_LD_JSON = re.compile(
    r'<script type="application/ld\+json">(.*?)</script>', re.S
)


class AttraxScraper(BaseScraper):
    """Sous-classer et definir ``key``, ``base_url``, ``country``.
    Ne pas enregistrer cette classe: elle n'a pas de ``key``."""

    # Racine du site, ex. "https://careers.abbvie.com"
    base_url: ClassVar[str] = ""
    # Segment de langue du site, ex. "en"
    locale: ClassVar[str] = "en"
    # Code ISO du filtre pays tel que l'attend le site, ex. "BE"
    country: ClassVar[str] = ""
    # Offres par page, impose par le site
    page_size: ClassVar[int] = 10
    # Garde-fou: au-dela, on considere que la pagination boucle
    max_pages: ClassVar[int] = 30
    rate_limit: ClassVar[float] = 0.4

    # ------------------------------------------------------------ recuperation

    def fetch(self) -> list[JobPosting]:
        urls = self._list_urls()
        return [posting for url in urls if (posting := self._job_from_detail(url))]

    def _list_urls(self) -> list[str]:
        """URL de chaque offre, dedoublonnees, dans l'ordre du site."""
        urls: list[str] = []
        seen: set[str] = set()

        for page in range(1, self.max_pages + 1):
            soup = self.get_soup(self._list_url(page))
            links = soup.select("a.attrax-vacancy-tile__title[href]")
            if not links:
                break

            new = 0
            for a in links:
                url = self.absolutize(a["href"])
                if url not in seen:
                    seen.add(url)
                    urls.append(url)
                    new += 1

            if len(links) < self.page_size:
                break
            if not new:
                # La pagination se repete: mieux vaut s'arreter que boucler
                break

        return urls

    def _list_url(self, page: int) -> str:
        base = f"{self.base_url.rstrip('/')}/{self.locale.strip('/')}/jobs"
        return f"{base}?q=&li={self.country}&page={page}"

    # ------------------------------------------------------------- conversion

    def _job_from_detail(self, url: str) -> JobPosting | None:
        """La fiche complete, via son bloc JSON-LD schema.org.

        Une fiche illisible ne doit pas faire echouer tout le scrape: on la
        journalise et on l'ignore plutot que de perdre le run entier pour une
        seule offre.
        """
        try:
            data = self._job_posting(url)
        except Exception as exc:  # noqa: BLE001
            log.warning("fiche %s illisible (%s), ignoree", url, exc)
            return None
        if data is None:
            log.warning("aucun JobPosting JSON-LD sur %s, ignoree", url)
            return None

        identifier = (data.get("identifier") or {}).get("value")
        industry = data.get("industry") or []
        return JobPosting(
            title=(data.get("title") or "").strip(),
            url=data.get("url") or url,
            location=_locations(data),
            description=html_to_text(data.get("description") or ""),
            department=", ".join(industry) if industry else None,
            posted_at=_as_date(data.get("datePosted")),
            # UUID du poste, expose par le site: survit a un changement de
            # titre ou de slug d'URL, contrairement au fingerprint calcule.
            external_id=str(identifier) if identifier else None,
        )

    def _job_posting(self, url: str) -> dict[str, Any] | None:
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        self.sleep()

        for block in _LD_JSON.findall(response.text):
            try:
                data = json.loads(block)
            except ValueError:
                continue
            if data.get("@type") == "JobPosting":
                return data
        return None


def _locations(data: dict[str, Any]) -> str | None:
    places = [
        (loc.get("address") or {}).get("addressLocality", "")
        for loc in data.get("jobLocation") or []
    ]
    return ", ".join(dict.fromkeys(p.strip() for p in places if p and p.strip())) or None


def _as_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None
