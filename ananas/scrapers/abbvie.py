"""AbbVie Belgium — site carrieres Attrax, filtre pays.

Toute la mecanique est dans ``AttraxScraper``; il ne reste ici que le pays a
declarer. Contrairement a Phenom (GSK, voir ``gsk.py``), le filtre ``li=BE``
d'Attrax est un filtre pays exact, pas une recherche de proximite: aucun
post-filtrage n'est necessaire.

Verifie le 2026-09-02: 2 offres pour la Belgique (Wavre), identifiant stable
(UUID JSON-LD) sur chacune.
"""

from __future__ import annotations

from ananas.scrapers.attrax import AttraxScraper
from ananas.scrapers.registry import register


@register
class AbbVieBelgiumScraper(AttraxScraper):
    key = "abbvie-belgium"
    label = "AbbVie Belgium"
    base_url = "https://careers.abbvie.com"
    country = "BE"
    careers_url = "https://careers.abbvie.com/en/jobs?q=&li=BE"
