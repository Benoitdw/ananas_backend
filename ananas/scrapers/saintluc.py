"""Cliniques universitaires Saint-Luc — Bruxelles (Woluwe). Talentsoft.

Verifie le 2026-09-08: 20 offres sur le flux "toutes offres" (pas de
pagination trouvee au-dela — la limite semble imposee par le site).
"""

from __future__ import annotations

from ananas.scrapers.registry import register
from ananas.scrapers.talentsoft import TalentsoftScraper


@register
class SaintLucScraper(TalentsoftScraper):
    key = "cliniques-universitaires-saint-luc"
    label = "Cliniques universitaires Saint-Luc"
    base_url = "https://jobs.saintluc.be"
    town = "Bruxelles"
    careers_url = "https://jobs.saintluc.be/offre-de-emploi/liste-toutes-offres.aspx?all=1"
