"""Base pour les sites carrieres Radancy (ex-TMP Worldwide).

Contrairement a Phenom, ces sites rendent leurs resultats en HTML classique:
pas d'etat JavaScript a decoder.

Le point fort: chaque fiche publie un bloc **schema.org JobPosting** en
JSON-LD. C'est un standard, donc une source bien plus sure que des selecteurs
CSS — elle survit aux refontes graphiques. On y prend la description, la date
et surtout **le pays**, qui sert de filtre.

Deux limites de la plateforme, verifiees et contournees ici:

1. **Le chemin ``/search-jobs/<X>/`` est une recherche par mot-cle**, pas un
   filtre de lieu: chercher "Belgium" remonte les annonces qui *mentionnent*
   la Belgique. D'ou le filtrage strict sur ``addressCountry`` du JSON-LD.
2. **La pagination d'une recherche filtree est cassee cote site.** Toutes les
   formes essayees (``?p=``, ``&p=``, ``/2/``, ``/page/2``, l'endpoint AJAX)
   perdent le filtre et renvoient le catalogue entier. On se limite donc a la
   premiere page, et on **journalise un avertissement** si le site annonce plus
   de resultats qu'on n'en a lu: une troncature doit se voir, pas se subir.
"""

from __future__ import annotations

import html as html_mod
import logging
import re
from datetime import date, datetime
from typing import Any, ClassVar
from urllib.parse import quote, urljoin

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import get_soup, html_to_text, jsonld_job_posting, txt

log = logging.getLogger(__name__)


class RadancyScraper(BaseScraper):
    """Sous-classer et definir ``key``, ``base_url`` et ``search_path``."""

    # Racine du site, ex. "https://jobs.sanofi.com"
    base_url: ClassVar[str] = ""
    # Chemin de recherche, ex. "/en/search-jobs/Belgium/"
    search_path: ClassVar[str] = ""
    # Pays acceptes, en majuscules. Plusieurs orthographes sont necessaires:
    # schema.org autorise le code ISO comme le nom, et les sites melangent les
    # deux ("BE", "Belgium", "Belgique"). Vide = pas de filtre.
    countries: ClassVar[frozenset[str]] = frozenset()
    rate_limit: ClassVar[float] = 0.4

    def fetch(self) -> list[JobPosting]:
        cards = self._collect()
        postings = [self._to_posting(card) for card in cards]

        if self.countries:
            kept = [p for p in postings if p.raw.get("country") in self.countries]
            log.info(
                "%s: %d offres listees, %d retenues (%s)",
                self.key,
                len(postings),
                len(kept),
                "/".join(sorted(self.countries)),
            )
            if postings and not kept:
                # Un filtre qui rejette tout est plus probablement mal regle
                # qu'un site reellement vide: il faut que ça se voie.
                log.warning(
                    "%s: aucune offre retenue. Pays vus: %s",
                    self.key,
                    sorted({p.raw.get("country", "?") for p in postings}),
                )
            return kept

        log.info("%s: %d offres listees", self.key, len(postings))
        return postings

    # ---------------------------------------------------------------- listing

    def _collect(self) -> list[dict[str, Any]]:
        """Premiere page uniquement — voir la limite 2 en tete de module."""
        soup = get_soup(urljoin(self.base_url, self.search_path), sess=self.session)
        self.sleep()

        cards = [self._parse_card(li) for li in soup.select("#search-results-list li")]
        cards = [c for c in cards if c]

        total = self._total(soup)
        if total > len(cards):
            # Rendre la troncature visible: sans ce message, des offres
            # disparaitraient sans que personne le sache.
            log.warning(
                "%s: le site annonce %d offres mais n'en expose que %d sans pagination. "
                "Restreins la recherche (ville plutot que pays) pour les voir toutes.",
                self.key,
                total,
                len(cards),
            )
        return cards

    @staticmethod
    def _total(soup) -> int:
        node = soup.select_one("[data-total-results]")
        try:
            return int(node["data-total-results"]) if node else 0
        except (KeyError, ValueError):
            return 0

    def _parse_card(self, li) -> dict[str, Any] | None:
        link = li.select_one("a[data-job-id]")
        if not link or not link.get("href"):
            return None
        return {
            # data-job-id est l'identifiant interne de l'offre: stable, il
            # survit a un changement d'intitule ou de slug d'URL.
            "job_id": link["data-job-id"],
            "url": urljoin(self.base_url, link["href"]),
            "title": txt(link.select_one("h2")),
            "location": _after_label(txt(link.select_one(".job-location"))),
            "category": _after_label(txt(link.select_one(".job-category"))),
        }

    # ------------------------------------------------------------------ fiche

    def _to_posting(self, card: dict[str, Any]) -> JobPosting:
        detail = self._detail(card["url"])
        return JobPosting(
            title=card["title"] or detail.get("title", ""),
            url=card["url"],
            location=detail.get("location") or card["location"] or None,
            department=card["category"] or None,
            description=detail.get("description", ""),
            posted_at=detail.get("posted_at"),
            external_id=card["job_id"],
            # `raw` ne participe pas au fingerprint: il ne sert qu'au filtrage
            raw={"country": detail.get("country", "")},
        )

    def _detail(self, url: str) -> dict[str, Any]:
        """Donnees de la fiche. Vide si elle est indisponible: on garde alors
        l'offre avec les seules informations de la liste."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            self.sleep()
            posting = jsonld_job_posting(response.text)
        except Exception as exc:  # noqa: BLE001
            log.warning("fiche %s illisible (%s)", url, exc)
            return {}

        if not posting:
            return {}

        return {
            "title": (posting.get("title") or "").strip(),
            "description": html_to_text(html_mod.unescape(posting.get("description") or "")),
            "posted_at": _as_date(posting.get("datePosted")),
            "location": _jsonld_places(posting.get("jobLocation")),
            "country": _jsonld_country(posting.get("jobLocation")),
        }


def _after_label(value: str) -> str:
    """Les cartes rendent "Location: Geel": on ne garde que la valeur."""
    return value.split(":", 1)[-1].strip() if ":" in value else value.strip()


def _jsonld_places(node: Any) -> str:
    """Villes listees dans le bloc schema.org, dedoublonnees."""
    nodes = node if isinstance(node, list) else [node] if node else []
    villes = []
    for place in nodes:
        address = (place or {}).get("address") or {}
        if ville := (address.get("addressLocality") or "").strip():
            villes.append(ville)
    return ", ".join(dict.fromkeys(villes))[:255]


def _jsonld_country(node: Any) -> str:
    """Code pays de la premiere adresse. C'est le filtre qui garantit qu'une
    recherche par mot-cle ne fait pas entrer d'offre etrangere."""
    nodes = node if isinstance(node, list) else [node] if node else []
    for place in nodes:
        country = ((place or {}).get("address") or {}).get("addressCountry")
        if isinstance(country, dict):
            country = country.get("name")
        if country:
            return str(country).strip().upper()
    return ""


def _as_date(value: str | None) -> date | None:
    """Radancy publie parfois "2026-8-4", que fromisoformat refuse."""
    if not value:
        return None
    if m := re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", value.strip()):
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None
