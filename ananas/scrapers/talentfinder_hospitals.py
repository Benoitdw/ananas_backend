"""Deux hopitaux sur TalentFinder (voir ``talentfinder.py``).

- **Clinique Saint-Pierre Ottignies** (``emploi.cspo.be``): la Liste An suit la
  categorie « Medico-technique ». Fiches sans JSON-LD: lecture du HTML.
- **CHU Helora** (Braine-l'Alleud, Mons, Jolimont, Binche, La Louviere): le
  site ``jobsparamedicalhelora.talentfinder.be`` ne couvre que le paramedical.

Verifie le 2026-11-19: 1 offre (Saint-Pierre, medico-technique), 0 (Helora).
"""

from __future__ import annotations

from ananas.scrapers.registry import register
from ananas.scrapers.talentfinder import TalentFinderScraper


@register
class CliniqueSaintPierreOttigniesScraper(TalentFinderScraper):
    key = "clinique-saint-pierre-ottignies"
    label = "Clinique Saint-Pierre Ottignies"
    default_location = "Ottignies"
    careers_url = "https://emploi.cspo.be/fr/vacatures/c/medico-technique-17752/index.aspx"


@register
class CHUHeloraScraper(TalentFinderScraper):
    key = "chu-helora"
    label = "CHU Helora (paramedical)"
    careers_url = "https://jobsparamedicalhelora.talentfinder.be/index.aspx"
