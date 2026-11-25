"""VUB (Vrije Universiteit Brussel) — Elsene et Jette. SAP SuccessFactors.

La Liste An suit la categorie anglaise « EN_ALL-JOBS » (``/go/EN_ALL-JOBS/
3775601/``): les annonces en anglais. La recherche generale du site
(``/search/``) melange les versions neerlandaises et anglaises (24 offres au
lieu de 12), et le flux RSS de la categorie n'en donne que 10: on lit donc la
page de la categorie, paginee par ``/<startrow>/``.

Verifie le 2026-11-25: 12 offres.
"""

from __future__ import annotations

from ananas.scrapers.registry import register
from ananas.scrapers.successfactors import SuccessFactorsScraper

BASE_URL = "https://jobs.vub.be"
CATEGORY = "/go/EN_ALL-JOBS/3775601/"


@register
class VubScraper(SuccessFactorsScraper):
    key = "vub"
    label = "VUB"
    base_url = BASE_URL
    careers_url = f"{BASE_URL}{CATEGORY}"
    search_location = ""
    location_tokens = frozenset()

    def page_url(self, startrow: int) -> str:
        return f"{BASE_URL}{CATEGORY}{startrow}/?q=" if startrow else f"{BASE_URL}{CATEGORY}?q="
