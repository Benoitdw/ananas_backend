"""Novartis Pharma (Belgique) — site carrieres Workday.

Contrairement a Pfizer, ce tenant **n'expose pas** la facette
``Location_Country``. On passe donc par la recherche texte (``search_text``)
puis on re-filtre sur le ``country`` du JSON de detail : la recherche Workday
matche le lieu, mais laisserait passer une annonce etrangere qui mentionne la
Belgique.

Les postes belges sont a Puurs ; le repertoire situe "Novartis Pharma" a
Vilvoorde (affaires commerciales). Le scraper couvre tout le pays, comme
Sanofi (voir ``sanofi.py``).

Verifie le 2026-09-02 : 16 offres renvoyees par la recherche, toutes belges.
"""

from __future__ import annotations

from ananas.scrapers.registry import register
from ananas.scrapers.workday import WorkdayScraper


@register
class NovartisPharmaScraper(WorkdayScraper):
    key = "novartis-pharma"
    label = "Novartis Pharma"
    host = "https://novartis.wd3.myworkdayjobs.com"
    tenant = "novartis"
    site = "Novartis_Careers"
    search_text = "Belgium"
    careers_url = "https://novartis.wd3.myworkdayjobs.com/Novartis_Careers"
