"""Sanofi Belgium — site carrieres Radancy.

Sanofi ne separe pas ses sites belges dans son moteur: le perimetre le plus
fin est le pays, ce qui correspond a l'entreprise "Sanofi Belgium" du
repertoire — les offres couvrent Machelen, Diegem et Geel.

Le chemin ``/search-jobs/Belgium/`` est une recherche par *mot-cle*: elle
remonterait une annonce parisienne qui mentionne la Belgique. ``country_code``
impose donc un filtre strict sur le pays declare dans le JSON-LD de chaque
fiche.

Verifie le 2026-09-02: 5 offres, toutes en Belgique.
"""

from __future__ import annotations

from ananas.scrapers.radancy import RadancyScraper
from ananas.scrapers.registry import register


@register
class SanofiBelgiumScraper(RadancyScraper):
    key = "sanofi-belgium"
    label = "Sanofi Belgium"
    base_url = "https://jobs.sanofi.com"
    search_path = "/en/search-jobs/Belgium/"
    countries = frozenset({"BE", "BELGIUM", "BELGIQUE", "BELGIE", "BELGIË"})
    careers_url = "https://jobs.sanofi.com/en/search-jobs/Belgium/"
