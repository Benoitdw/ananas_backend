"""Univercells Technologies — site carrieres Workday du groupe Donaldson.

Depuis le rachat par Donaldson (Life Sciences), les offres passent par le
Workday Donaldson (`donaldson.wd115` / site `DonaldsonCareers`). Ce tenant
n'expose pas de facette pays : recherche texte ``"Belgium"``, puis on ne garde
que les postes de **Nivelles** — les autres postes belges de Donaldson
(Leuven, filtration) ne sont pas Univercells Technologies.

Verifie le 2026-09-02 : 2 offres (Nivelles).
"""

from __future__ import annotations

from ananas.scrapers.registry import register
from ananas.scrapers.workday import WorkdayScraper


@register
class UnivercellsTechnologiesScraper(WorkdayScraper):
    key = "univercells-technologies"
    label = "Univercells Technologies"
    host = "https://donaldson.wd115.myworkdayjobs.com"
    tenant = "donaldson"
    site = "DonaldsonCareers"
    search_text = "Belgium"
    location_tokens = frozenset({"nivelles"})
    careers_url = "https://donaldson.wd115.myworkdayjobs.com/en-US/DonaldsonCareers"
