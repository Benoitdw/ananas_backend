"""Zoetis Belgium — Zaventem (siege EMEA). Workday ``zoetis_intl``.

La page ``zoetis.com/join-us/international-careers`` est une vitrine: elle
interroge un index Solr (Crownpeak SearchG2) qui renvoie, pour chaque poste,
l'URL de la fiche sur le Workday international de Zoetis
(``zoetis.wd5.myworkdayjobs.com/zoetis_intl``). On va directement au Workday,
qui donne la description complete.

Ce tenant n'a pas de facette pays mais une facette ``locations`` (sites): le
seul site belge est Zaventem. Si Zoetis ouvre un autre site belge, il faudra
ajouter son WID (lisible dans la reponse ``facets`` de l'API).

Verifie le 2026-11-19: 3 offres (Zaventem).
"""

from __future__ import annotations

from ananas.scrapers.registry import register
from ananas.scrapers.workday import WorkdayScraper


@register
class ZoetisBelgiumScraper(WorkdayScraper):
    key = "zoetis-belgium"
    label = "Zoetis Belgium"
    host = "https://zoetis.wd5.myworkdayjobs.com"
    tenant = "zoetis"
    site = "zoetis_intl"
    country_facet = "locations"
    country_facet_wid = "2d5efb14629b10322cd753de053112bf"  # Zaventem
    careers_url = "https://www.zoetis.com/join-us/international-careers"
