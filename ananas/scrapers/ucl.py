"""UCLouvain — Louvain-la-Neuve. SuccessFactors jobs2web, deux categories.

Le repertoire suit separement le personnel administratif et le personnel
scientifique (deux fiches, deux ``key``): meme site, deux ``catid`` de flux
RSS trouves sur https://jobs.uclouvain.be/.

Verifie le 2026-09-08: 10 offres (administratif), 4 offres (scientifique).
"""

from __future__ import annotations

from ananas.scrapers.jobs2web import Jobs2WebScraper
from ananas.scrapers.registry import register

BASE_URL = "https://jobs.uclouvain.be"


@register
class UCLouvainPersonnelAdministratifScraper(Jobs2WebScraper):
    key = "ucl-personnels-administratifs"
    label = "UCLouvain - Personnel administratif et technique"
    base_url = BASE_URL
    category_id = "3272401"
    careers_url = f"{BASE_URL}/PersonnelAdministratif/go/UCLouvain-Personnel-administratif-et-technique/3272401/"


@register
class UCLouvainPersonnelScientifiqueScraper(Jobs2WebScraper):
    key = "ucl-personnels-scientifiques"
    label = "UCLouvain - Personnel scientifique"
    base_url = BASE_URL
    category_id = "3272501"
    careers_url = f"{BASE_URL}/Personnelscientifique/go/UCLouvain-Personnel-scientifique/3272501/"
