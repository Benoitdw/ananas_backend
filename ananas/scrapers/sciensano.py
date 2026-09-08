"""Sciensano — Ixelles (siege) / sites a Anderlecht, Machelen. API HR-Technologies.

Verifie le 2026-09-08: 7 offres (dont plusieurs stages), lieu structure par
offre (pas de lieu unique a plaquer, contrairement a Saint-Luc).
"""

from __future__ import annotations

from ananas.scrapers.hr_technologies import HRTechnologiesScraper
from ananas.scrapers.registry import register


@register
class SciensanoScraper(HRTechnologiesScraper):
    key = "sciensano"
    label = "Sciensano"
    client_uuid = "80deda9d-3123-4d38-9c81-16b6ccfec4c7"
    front_url = "https://jobs.sciensano.be/front/fr"
    careers_url = "https://jobs.sciensano.be/front/fr/"
