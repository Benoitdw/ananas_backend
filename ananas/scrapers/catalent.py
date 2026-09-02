"""Catalent — site carrieres Phenom People (``careers.catalent.com``).

Meme plateforme que GSK / Roche / MSD (``phApp.ddo``). Le segment de langue
est ``us/en`` (la racine y redirige) ; ``qcountry`` est une recherche de
*proximite*, on re-filtre donc sur ``location_tokens``.

Catalent n'a pas de site belge : au 2026-09-02 la recherche ``qcountry=Belgium``
renvoie 0 poste. Le scraper est pose quand meme (comme BMS) — il remontera les
offres des qu'il y en aura, sans intervention.
"""

from __future__ import annotations

from ananas.scrapers.phenom import PhenomScraper
from ananas.scrapers.registry import register


@register
class CatalentScraper(PhenomScraper):
    key = "catalent"
    label = "Catalent"
    base_url = "https://careers.catalent.com"
    locale_path = "us/en"
    search_params = {"qcountry": "Belgium"}
    location_tokens = frozenset({"belgium"})
    careers_url = "https://careers.catalent.com/us/en/search-results?qcountry=Belgium"
