"""GSK — sites de Wavre et de Rixensart.

Deux entreprises distinctes dans le repertoire: ce sont deux sites industriels
separes, avec des offres differentes, et on veut pouvoir suivre l'un sans
l'autre. Toute la mecanique est dans ``PhenomScraper``; il ne reste ici que le
lieu a declarer.

Attention: la recherche par lieu de GSK est une recherche de *proximite*.
"Rixensart" renvoie une cinquantaine de postes dont plusieurs a Londres ou
Collegeville. ``town`` sert au filtrage effectif — voir PhenomScraper._is_local.

Verifie le 2026-09-02: 51 offres retenues pour Wavre, 10 pour Rixensart.
"""

from __future__ import annotations

from ananas.scrapers.phenom import PhenomScraper
from ananas.scrapers.registry import register


class GskScraper(PhenomScraper):
    base_url = "https://jobs.gsk.com"
    locale_path = "be/fr"


@register
class GskWavreScraper(GskScraper):
    key = "gsk-wavre"
    label = "GSK — Wavre"
    town = "Wavre"
    # m=3 : recherche par proximite, seul mode accepte par cette instance
    search_params = {"m": "3", "location": "Wavre, Brabant wallon, Belgique"}
    careers_url = (
        "https://jobs.gsk.com/be/fr/search-results"
        "?m=3&location=Wavre%2C%20Brabant%20wallon%2C%20Belgique"
    )


@register
class GskRixensartScraper(GskScraper):
    key = "gsk-rixensart"
    label = "GSK — Rixensart"
    town = "Rixensart"
    search_params = {"m": "3", "location": "Rixensart, Brabant wallon, Belgique"}
    careers_url = (
        "https://jobs.gsk.com/be/fr/search-results"
        "?m=3&location=Rixensart%2C%20Brabant%20wallon%2C%20Belgique"
    )
