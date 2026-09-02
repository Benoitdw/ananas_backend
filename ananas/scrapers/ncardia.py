"""Ncardia (Gosselies) et sa base de scraper commune avec Cellistic.

Ncardia et Cellistic (spin-off iPSC) partagent le meme constructeur de site :
la page ``/careers`` liste les postes en clair, un lien ``/careers/<slug>`` par
poste, avec ``<span class="location">Ville, Pays</span>`` ; la fiche porte le
titre en ``h1``, le lieu en ``.location`` et le corps dans ``main``.

``SlugCareersScraper`` factorise ce parsing ; ``location_tokens`` filtre le
pays (Ncardia ouvre aussi des postes a Leiden, aux Pays-Bas).

Verifie le 2026-09-02 : Ncardia 0 offre en Belgique (1 a Leiden).
"""

from __future__ import annotations

import logging
import re
from typing import ClassVar
from urllib.parse import urljoin

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import txt
from ananas.scrapers.registry import register

log = logging.getLogger(__name__)


class SlugCareersScraper(BaseScraper):
    """Sous-classer et definir ``key``, ``label``, ``base_url``."""

    base_url: ClassVar[str] = ""
    # Jetons retenus sur le libelle de lieu. Vide = tout est retenu.
    location_tokens: ClassVar[frozenset[str]] = frozenset({"belg"})
    rate_limit: ClassVar[float] = 0.3

    def fetch(self) -> list[JobPosting]:
        soup = self.get_soup(self.careers_url)
        stubs = []
        for a in soup.select('a[href^="/careers/"], a[href*="/careers/"]'):
            href = a.get("href", "")
            if re.sub(r"[/#?].*$", "", href.rstrip("/")).endswith("careers"):
                continue  # lien vers la page carrieres elle-meme
            loc_node = a.select_one(".location, span.location")
            location = txt(loc_node)
            title = txt(a)
            if loc_node and location and location in title:
                title = title[: title.rindex(location)].strip(" -–|")
            stubs.append((urljoin(self.base_url, href), title, location))

        seen: set[str] = set()
        postings = []
        for url, title, location in stubs:
            if url in seen:
                continue
            seen.add(url)
            if self.location_tokens and not any(
                tok in location.casefold() for tok in self.location_tokens
            ):
                continue
            postings.append(self._to_posting(url, title, location))

        log.info(
            "%s: %d liens, %d retenus (%s)",
            self.key,
            len(seen),
            len(postings),
            "/".join(sorted(self.location_tokens)) or "tous",
        )
        return postings

    def _to_posting(self, url: str, title: str, location: str) -> JobPosting:
        detail = self._detail(url)
        return JobPosting(
            title=detail.get("title") or title,
            url=url,
            location=detail.get("location") or location or None,
            description=detail.get("description", ""),
            external_id=url.rstrip("/").rsplit("/", 1)[-1],
        )

    def _detail(self, url: str) -> dict[str, str]:
        try:
            soup = self.get_soup(url)
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: fiche %s illisible (%s)", self.key, url, exc)
            return {}
        h1 = soup.select_one("h1")
        loc = soup.select_one("[class*=location]")
        body = soup.select_one("main, article, .job-content")
        return {
            "title": txt(h1),
            "location": txt(loc),
            "description": txt(body)[:8000],
        }


@register
class NcardiaScraper(SlugCareersScraper):
    key = "ncardia"
    label = "Ncardia"
    base_url = "https://www.ncardia.com"
    careers_url = "https://www.ncardia.com/careers"
