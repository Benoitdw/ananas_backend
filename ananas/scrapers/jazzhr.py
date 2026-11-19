"""Base pour les sites carrieres JazzHR (``<sous-domaine>.applytojob.com``).

La liste ``/apply/jobs/`` est rendue cote serveur et couvre tous les sites du
groupe: chaque offre est un lien ``/apply/jobs/details/<code>`` suivi de son
lieu ("Wilrijk, Antwerp, Belgium"). On filtre sur ce lieu avant d'ouvrir les
fiches, qui publient un bloc schema.org ``JobPosting`` en JSON-LD.

``<code>`` est l'identifiant JazzHR de l'offre, stable.
"""

from __future__ import annotations

import html as html_mod
import logging
import re
from datetime import date, datetime
from typing import ClassVar
from urllib.parse import urljoin

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import html_to_text, jsonld_job_posting, txt

log = logging.getLogger(__name__)

_DETAILS = re.compile(r"/apply/jobs/details/([A-Za-z0-9]+)")


class JazzHRScraper(BaseScraper):
    """Sous-classer et definir ``key``, ``jazz_slug`` et ``location_tokens``.

    Ne pas enregistrer cette classe: elle n'a pas de ``key``.
    """

    jazz_slug: ClassVar[str] = ""
    # Jetons de lieu retenus (insensibles a la casse). Vide = tout le groupe.
    location_tokens: ClassVar[frozenset[str]] = frozenset()
    rate_limit: ClassVar[float] = 0.4

    def fetch(self) -> list[JobPosting]:
        root = f"https://{self.jazz_slug}.applytojob.com/apply/jobs/"
        soup = self.get_soup(root)
        toks = {t.casefold() for t in self.location_tokens}
        stubs: dict[str, tuple[str, str]] = {}
        # Chaque offre est une ligne de tableau : lien (titre) | lieu. La page
        # repete les offres dans un second bloc sans lieu, d'ou le <tr>.
        for row in soup.select("tr"):
            a = row.select_one("a[href*='/apply/jobs/details/']")
            match = _DETAILS.search(a["href"]) if a else None
            if not match:
                continue
            location = txt(row).replace(txt(a), "", 1).strip()
            if toks and not any(t in location.casefold() for t in toks):
                continue
            stubs.setdefault(match.group(1), (txt(a), location))

        postings = [
            self._detail(urljoin(root, f"details/{code}"), code, title, location)
            for code, (title, location) in stubs.items()
        ]
        log.info("%s: %d offres", self.key, len(postings))
        return postings

    def _detail(self, url: str, code: str, title: str, location: str) -> JobPosting:
        description, posted = "", None
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            self.sleep()
            ld = jsonld_job_posting(response.text) or {}
            description = html_to_text(html_mod.unescape(ld.get("description") or ""))
            posted = _as_date(ld.get("datePosted"))
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: fiche %s illisible (%s)", self.key, url, exc)
        return JobPosting(
            title=title,
            url=url,
            location=location or None,
            description=description,
            posted_at=posted,
            external_id=code,
        )


def _as_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value[:10]).date()
    except ValueError:
        return None
