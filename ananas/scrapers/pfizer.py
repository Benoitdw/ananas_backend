"""Pfizer Belgium — site carrieres Workday.

Toute la mecanique est dans ``WorkdayScraper``. Pfizer expose la facette
``Location_Country`` : un filtre exact cote serveur, le WID "Belgium" suffit,
aucun re-filtrage necessaire.

Le repertoire situe "Pfizer Belgium" a Bruxelles (siege commercial), mais
l'essentiel des postes belges est a l'usine de Puurs — le scraper couvre donc
tout le pays, comme Sanofi (voir ``sanofi.py``).

Verifie le 2026-09-02 : 9 offres, toutes en Belgique, ``jobReqId`` stable sur
chacune.
"""

from __future__ import annotations

from ananas.scrapers.registry import register
from ananas.scrapers.workday import WorkdayScraper


@register
class PfizerBelgiumScraper(WorkdayScraper):
    key = "pfizer-belgium"
    label = "Pfizer Belgium"
    host = "https://pfizer.wd1.myworkdayjobs.com"
    tenant = "pfizer"
    site = "PfizerCareers"
    country_facet_wid = "a04ea128f43a42e59b1e6a19e8f0b374"
    careers_url = "https://pfizer.wd1.myworkdayjobs.com/PfizerCareers"
