"""CellCarta — Anvers (Wilrijk). JazzHR ``caprion.applytojob.com``.

CellCarta (ex-Caprion) publie tous ses sites (Canada, Etats-Unis, Australie,
Belgique) sur le meme compte JazzHR. On ne garde que la Belgique.

Verifie le 2026-11-19: 7 offres a Wilrijk sur 17.
"""

from __future__ import annotations

from ananas.scrapers.jazzhr import JazzHRScraper
from ananas.scrapers.registry import register


@register
class CellCartaScraper(JazzHRScraper):
    key = "cellcarta"
    label = "CellCarta"
    jazz_slug = "caprion"
    location_tokens = frozenset({"belgium", "belgique"})
    careers_url = "https://cellcarta.com/fr/carrieres/"
