"""Base pour les sites carrieres SAP SuccessFactors (Recruiting / RCM).

SuccessFactors equipe une partie des groupes pharma/medtech (Boehringer
Ingelheim, Terumo, Bausch + Lomb…). Contrairement a Phenom, **la liste est
rendue cote serveur** : pas d'etat JavaScript a decoder, du HTML classique.

Deux themes coexistent selon l'age de l'instance, tous deux geres ici :

- ancien : un tableau, une offre par ``tr.data-row`` (Terumo) ;
- recent : des vignettes, une offre par ``li.job-tile`` (Boehringer).

Pieges verifies et contournes :

1. **``locationsearch=<pays>`` est une recherche de proximite**, pas un filtre :
   elle laisse passer des postes frontaliers ou multi-pays. On re-filtre donc
   sur ``location_tokens`` (le libelle de lieu de la liste porte toujours le
   nom du pays).
2. **La pagination se fait par ``startrow``** (offset 0-indexe, pas de la
   page). Le pas est ``page_step`` (25 par defaut, impose par le site).
3. **La liste ne porte pas toujours la description ni la date.** On ouvre donc
   la fiche : ``[itemprop="description"]`` pour le texte,
   ``[itemprop="datePosted"]`` (attribut ``content``) pour la date, avec repli
   sur la date affichee dans la liste quand elle existe.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Any, ClassVar
from urllib.parse import urlencode, urljoin

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import html_to_text

log = logging.getLogger(__name__)

# `/job/<slug>/<id>/` — l'identifiant numerique est la reference publique du
# poste, stable d'un run a l'autre malgre un changement de titre ou de slug.
_JOB_ID = re.compile(r"/job/[^/]+/(\d+)/?")


class SuccessFactorsScraper(BaseScraper):
    """Sous-classer et definir ``key`` et ``base_url``."""

    # Racine du site, ex. "https://jobs.boehringer-ingelheim.com"
    base_url: ClassVar[str] = ""
    # Valeur passee a ``locationsearch`` (pre-filtre serveur). Vide = tout le site.
    search_location: ClassVar[str] = "Belgium"
    # Jetons retenus apres coup sur le libelle de lieu. Vide = pas de re-filtrage.
    location_tokens: ClassVar[frozenset[str]] = frozenset({"belgium", "belgi", "belg/"})
    # Pas de pagination impose par SuccessFactors
    page_step: ClassVar[int] = 25
    # Garde-fou: au-dela, on considere que la pagination boucle
    max_pages: ClassVar[int] = 20
    rate_limit: ClassVar[float] = 0.4

    # ------------------------------------------------------------ recuperation

    def fetch(self) -> list[JobPosting]:
        stubs = self._list()
        kept = [s for s in stubs if self._is_local(s)]
        log.info(
            "%s: %d offres listees, %d retenues (%s)",
            self.key,
            len(stubs),
            len(kept),
            "/".join(sorted(self.location_tokens)) or "toutes",
        )
        if stubs and not kept and self.location_tokens:
            log.warning(
                "%s: aucune offre retenue. Lieux vus : %s",
                self.key,
                sorted({s["location"] for s in stubs}),
            )
        return [self._to_posting(s) for s in kept]

    def _list(self) -> list[dict[str, Any]]:
        stubs: list[dict[str, Any]] = []
        seen: set[str] = set()

        for page in range(self.max_pages):
            params = {"q": "", "startrow": page * self.page_step}
            if self.search_location:
                params["locationsearch"] = self.search_location
            url = f"{self.base_url.rstrip('/')}/search/?{urlencode(params)}"
            soup = self.get_soup(url)

            batch = [self._parse_tile(node) for node in _tiles(soup)]
            batch = [b for b in batch if b]
            if not batch:
                break

            new = 0
            for stub in batch:
                if stub["id"] in seen:
                    continue
                seen.add(stub["id"])
                stubs.append(stub)
                new += 1

            total = _total(soup)
            if not new or (total and len(stubs) >= total):
                break

        return stubs

    def _parse_tile(self, node) -> dict[str, Any] | None:
        link = node.select_one("a.jobTitle-link") or node.select_one("a[href*='/job/']")
        href = link.get("href") if link else node.get("data-url")
        if not href:
            return None
        url = urljoin(self.base_url, href)
        m = _JOB_ID.search(url)

        loc_node = node.select_one(
            "[id*='section-location-value'], td.colLocation .jobLocation, .jobLocation"
        )
        date_node = node.select_one("td.colDate .jobDate, .jobDate")
        return {
            "id": m.group(1) if m else url,
            "url": url,
            "title": (link.get_text(" ", strip=True) if link else "").strip(),
            "location": loc_node.get_text(" ", strip=True) if loc_node else "",
            "list_date": _as_date(date_node.get_text(strip=True)) if date_node else None,
        }

    # -------------------------------------------------------------- filtrage

    def _is_local(self, stub: dict[str, Any]) -> bool:
        if not self.location_tokens:
            return True
        place = stub["location"].casefold()
        return any(tok in place for tok in self.location_tokens)

    # ------------------------------------------------------------ conversion

    def _to_posting(self, stub: dict[str, Any]) -> JobPosting:
        detail = self._detail(stub["url"])
        return JobPosting(
            title=stub["title"] or detail.get("title", ""),
            url=stub["url"],
            location=stub["location"] or detail.get("location") or None,
            description=detail.get("description", ""),
            posted_at=detail.get("posted_at") or stub["list_date"],
            external_id=stub["id"] if stub["id"].isdigit() else None,
        )

    def _detail(self, url: str) -> dict[str, Any]:
        """Contenu de la fiche. Vide si indisponible : l'offre est conservee
        avec les seules donnees de la liste."""
        try:
            soup = self.get_soup(url)
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: fiche %s illisible (%s)", self.key, url, exc)
            return {}

        desc = soup.select_one("[itemprop='description'], .jobDescriptionBody, .job")
        title = soup.select_one("[itemprop='title'], h1")
        date_node = soup.select_one("[itemprop='datePosted']")
        return {
            "title": title.get_text(" ", strip=True) if title else "",
            "description": html_to_text(desc.decode_contents()) if desc else "",
            "posted_at": _as_date(date_node.get("content") if date_node else None),
        }


# ------------------------------------------------------------------- parsing


def _tiles(soup) -> list:
    return soup.select("li.job-tile") or soup.select("tr.data-row")


def _total(soup) -> int:
    """"Results 1 - 14 of 14" / "Showing 1 to 2 of 2 Jobs"."""
    label = soup.select_one(
        ".paginationLabel, #tile-search-results-label, #search-results-label"
    )
    if not label:
        return 0
    m = re.search(r"of\s+([\d,]+)", label.get_text(" ", strip=True))
    return int(m.group(1).replace(",", "")) if m else 0


def _as_date(value: str | None) -> date | None:
    if not value:
        return None
    value = value.strip().replace("Sept", "Sep")
    for fmt in ("%d %b %Y", "%b %d, %Y", "%a %b %d %H:%M:%S %Z %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None
