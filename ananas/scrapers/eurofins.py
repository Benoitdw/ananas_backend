"""Eurofins Belgium — Bruxelles, Rixensart, Gand... API SmartRecruiters ``Eurofins``.

``careers.eurofins.com`` est une vitrine SmartRecruiters. Filtre exact
``country=be``. La Liste An filtrait sur trois departements du site Eurofins
(``deptid=14,15,24``), un identifiant propre a la vitrine qui n'a pas
d'equivalent dans l'API: on garde tout le pays, le score de correspondance
fait le tri.

Verifie le 2026-11-19: 36 offres en Belgique.
"""

from __future__ import annotations

from ananas.scrapers.registry import register
from ananas.scrapers.smartrecruiters import SmartRecruitersScraper


@register
class EurofinsBelgiumScraper(SmartRecruitersScraper):
    key = "eurofins-belgium"
    label = "Eurofins Belgium"
    sr_company = "Eurofins"
    country = "be"
    careers_url = "https://careers.eurofins.com/be-fr/jobs/?countryId=be"
