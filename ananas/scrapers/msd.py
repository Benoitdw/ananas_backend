"""MSD Belgium (Merck & Co.) — site carrieres Phenom People (``jobs.msd.com``).

Comme GSK, l'instance MSD traite ``qcountry`` comme une recherche de
*proximite* : interroger "Belgium" remonte aussi des postes a Prague ou
Milton Keynes. On re-filtre donc sur ``location_tokens`` : un poste est retenu
des qu'un de ses lieux porte "Belgium" — les postes belges de MSD comme les
roles europeens explicitement ouverts a la Belgique.

Verifie le 2026-09-02 : ~4 offres concernant la Belgique (siege de Bruxelles).
"""

from __future__ import annotations

from ananas.scrapers.phenom import PhenomScraper
from ananas.scrapers.registry import register


@register
class MsdBelgiumScraper(PhenomScraper):
    key = "msd-belgium"
    label = "MSD Belgium"
    base_url = "https://jobs.msd.com"
    locale_path = "gb/en"
    search_params = {"qcountry": "Belgium"}
    location_tokens = frozenset({"belgium"})
    careers_url = "https://jobs.msd.com/gb/en/belgium-job-search"
