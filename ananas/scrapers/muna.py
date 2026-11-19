"""Muna Therapeutics — Leuven. BambooHR ``muna``.

Le site (Gatsby) charge le widget BambooHR: ``muna.bamboohr.com``.

Verifie le 2026-11-19: 0 offre ouverte. Le schema de la liste BambooHR n'a donc
pas pu etre confronte a une offre reelle de Muna.
"""

from __future__ import annotations

from ananas.scrapers.bamboohr import BambooHRScraper
from ananas.scrapers.registry import register


@register
class MunaTherapeuticsScraper(BambooHRScraper):
    key = "muna-therapeutics"
    label = "Muna Therapeutics"
    bamboo_slug = "muna"
    careers_url = "https://munatherapeutics.com/careers/"
