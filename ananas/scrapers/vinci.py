"""Haute Ecole Leonard de Vinci — Woluwe. Site carrieres TalentSquare.

Le recrutement du personnel passe par ``vinci.talentsquare.com`` (et non par
le portail JobTeaser de ``vinci.be``, reserve aux etudiants — voir la note
« Bloquees » de SCRAPERS.md, levee par la Liste An).

Verifie le 2026-11-19: 5 offres.
"""

from __future__ import annotations

from ananas.scrapers.registry import register
from ananas.scrapers.talentsquare import TalentSquareScraper


@register
class HauteEcoleLeonardDeVinciScraper(TalentSquareScraper):
    key = "haute-ecole-leonard-de-vinci"
    label = "Haute Ecole Leonard de Vinci"
    ts_slug = "vinci"
    careers_url = "https://vinci.talentsquare.com/jobs/"
