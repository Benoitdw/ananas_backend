"""Cellistic (Mont-Saint-Guibert) — spin-off iPSC de Ncardia.

Meme constructeur de site que Ncardia : voir ``ncardia.py`` pour le parsing
(``SlugCareersScraper``). Site unique en Belgique.

Verifie le 2026-09-02 : 2 offres (Mont-Saint-Guibert).
"""

from __future__ import annotations

from ananas.scrapers.ncardia import SlugCareersScraper
from ananas.scrapers.registry import register


@register
class CellisticScraper(SlugCareersScraper):
    key = "cellistic"
    label = "Cellistic"
    base_url = "https://www.cellistic.com"
    careers_url = "https://www.cellistic.com/careers"
