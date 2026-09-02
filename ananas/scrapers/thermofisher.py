"""Thermo Fisher Scientific – Henogen — site carrieres Phenom People.

``jobs.thermofisher.com`` tourne sur Phenom (comme GSK / Roche / MSD). La
fiche du repertoire vise le site **de Gosselies** (ex-Henogen, therapie
genique/cellulaire) ; le groupe publie ~40 postes en Belgique, la plupart en
teletravail ou sur d'autres sites (Zaventem, Vilvoorde, Geel…).

On restreint donc via ``location_tokens`` a Gosselies et Seneffe (le pole
bioproduction wallon de Thermo Fisher). ``qcountry=Belgium`` sert de pre-filtre
de proximite cote serveur.

Verifie le 2026-09-02 : 3 offres (Seneffe) sur 43 postes belges du groupe.
"""

from __future__ import annotations

from ananas.scrapers.phenom import PhenomScraper
from ananas.scrapers.registry import register


@register
class ThermoFisherHenogenScraper(PhenomScraper):
    key = "thermo-fisher-scientific-henogen"
    label = "Thermo Fisher Scientific – Henogen"
    base_url = "https://jobs.thermofisher.com"
    locale_path = "global/en"
    search_params = {"qcountry": "Belgium"}
    location_tokens = frozenset({"gosselies", "seneffe"})
    careers_url = "https://jobs.thermofisher.com/global/en/search-results?qcountry=Belgium"
