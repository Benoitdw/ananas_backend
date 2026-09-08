"""Cap4HR — Waterloo. Site carrieres TalentSquare.

Cap4HR est une societe de conseil RH: les offres du widget sont, pour partie,
celles de ses clients (recrutement en marque blanche) plutot que des postes
internes a Cap4HR elle-meme — c'est le contenu que TalentSquare expose, il n'y
a pas de distinction possible cote scraper.

Verifie le 2026-09-08: 4 offres, toutes en Belgique.
"""

from __future__ import annotations

from ananas.scrapers.registry import register
from ananas.scrapers.talentsquare import TalentSquareScraper


@register
class Cap4HRScraper(TalentSquareScraper):
    key = "cap4hr"
    label = "Cap4HR"
    ts_slug = "cap4hr"
    careers_url = "https://cap4hr.talentsquare.com/careers"
