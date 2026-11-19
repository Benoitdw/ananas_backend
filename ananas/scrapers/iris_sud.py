"""Hopitaux Iris Sud — Bruxelles (Etterbeek-Ixelles, Molière, Bracops). Beehire.

Verifie le 2026-11-19: 26 offres.
"""

from __future__ import annotations

from ananas.scrapers.beehire import BeehireScraper
from ananas.scrapers.registry import register


@register
class HopitauxIrisSudScraper(BeehireScraper):
    key = "hopitaux-iris-sud"
    label = "Hopitaux Iris Sud"
    beehire_slug = "his-izz"
    careers_url = "https://app.beehire.com/career/his-izz"
