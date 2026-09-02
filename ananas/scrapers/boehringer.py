"""Boehringer Ingelheim — site carrieres SAP SuccessFactors.

``jobs.boehringer-ingelheim.com``, theme "vignettes" (``li.job-tile``). Les
postes belges sont a Bruxelles (Human Pharma + Animal Health, ROPU MIDI).

Verifie le 2026-09-02 : 2 offres (Bruxelles).
"""

from __future__ import annotations

from ananas.scrapers.registry import register
from ananas.scrapers.successfactors import SuccessFactorsScraper


@register
class BoehringerIngelheimScraper(SuccessFactorsScraper):
    key = "boehringer-ingelheim"
    label = "Boehringer Ingelheim"
    base_url = "https://jobs.boehringer-ingelheim.com"
    careers_url = "https://jobs.boehringer-ingelheim.com/search/?q=&locationsearch=Belgium"
