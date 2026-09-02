"""Roche (Diagnostics) Belgique — site carrieres Phenom People.

Meme plateforme que GSK (``phApp.ddo``). ``qcountry=Belgium`` est ici une
recherche de *proximite*, pas un filtre : on retient apres coup tout poste
dont un lieu porte "Belgium" (``location_tokens``), ce qui couvre le siege de
Bruxelles comme les postes multi-pays ouverts a la Belgique.

Verifie le 2026-09-02 : 1 offre (Bruxelles).
"""

from __future__ import annotations

from ananas.scrapers.phenom import PhenomScraper
from ananas.scrapers.registry import register


@register
class RocheBelgiumScraper(PhenomScraper):
    key = "roche-diagnostics"
    label = "Roche Diagnostics"
    base_url = "https://careers.roche.com"
    locale_path = "global/en"
    search_params = {"qcountry": "Belgium"}
    location_tokens = frozenset({"belgium"})
    careers_url = "https://careers.roche.com/global/en/search-results?qcountry=Belgium"
