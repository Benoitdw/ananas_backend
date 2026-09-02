"""UCB — sites de Braine-l'Alleud et d'Anderlecht.

Meme plateforme que GSK (Phenom People) mais **pas la meme facon de filtrer**:
cette instance ignore ``m=3&location=`` et attend le triplet structure
``qcity/qstate/qcountry``, qui filtre exactement au lieu d'approcher.

Deux details qui font perdre du temps si on ne les connait pas:

- UCB ecrit la ville ``Braine L'alleud`` — sans trait d'union, avec un `l`
  minuscule. Toute autre orthographe renvoie zero resultat.
- la recherche par mot-cle ne fonctionne pas sur cette ville: l'apostrophe
  casse l'indexation. Seul le filtre structure marche.

Verifie le 2026-09-02: 80 offres a Braine-l'Alleud, 46 a Anderlecht — soit
exactement les 126 offres belges annoncees par les facettes du site.
"""

from __future__ import annotations

from ananas.scrapers.phenom import PhenomScraper
from ananas.scrapers.registry import register


class UcbScraper(PhenomScraper):
    base_url = "https://careers.ucb.com"
    locale_path = "global/en"


@register
class UcbBraineScraper(UcbScraper):
    key = "ucb-pharma-braine-l-alleud"
    label = "UCB Pharma — Braine-l'Alleud"
    # Orthographe imposee par le site, ne pas "corriger"
    town = "Braine L'alleud"
    search_params = {
        "qcity": "Braine L'alleud",
        "qstate": "Walloon Brabant",
        "qcountry": "Belgium",
    }
    careers_url = "https://careers.ucb.com/global/en/search-results?qcity=Braine%20L%27alleud"


@register
class UcbAnderlechtScraper(UcbScraper):
    key = "ucb-anderlecht"
    label = "UCB — Anderlecht"
    town = "Anderlecht"
    search_params = {"qcity": "Anderlecht", "qstate": "Brussels", "qcountry": "Belgium"}
    careers_url = "https://careers.ucb.com/global/en/search-results?qcity=Anderlecht"
