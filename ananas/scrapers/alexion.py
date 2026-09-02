"""Alexion Pharma Belgium — site carrieres Workday du groupe AstraZeneca.

Alexion (maladies rares) partage le portail carrieres d'AstraZeneca. Ce tenant
n'expose pas de facette pays : recherche texte ``"Belgium"`` puis re-filtrage
sur le ``country`` du JSON de detail.

Comme il n'existe pas d'entree "AstraZeneca Belgium" distincte dans le
repertoire, ce scraper remonte **tous** les postes belges du groupe AstraZeneca
(Alexion inclus) sous la fiche "Alexion Pharma Belgium" — meme logique
d'entite nationale que Sanofi ou Pfizer.

Verifie le 2026-09-02 : 1 offre (Mont-Saint-Guibert).
"""

from __future__ import annotations

from ananas.scrapers.registry import register
from ananas.scrapers.workday import WorkdayScraper


@register
class AlexionBelgiumScraper(WorkdayScraper):
    key = "alexion-pharma-belgium"
    label = "Alexion Pharma Belgium"
    host = "https://astrazeneca.wd3.myworkdayjobs.com"
    tenant = "astrazeneca"
    site = "Careers"
    search_text = "Belgium"
    careers_url = "https://astrazeneca.wd3.myworkdayjobs.com/Careers"
