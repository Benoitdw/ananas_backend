"""Sobi (Swedish Orphan Biovitrum) — API SmartRecruiters.

Identifiant SmartRecruiters : ``Sobi``. Le filtre serveur ``country=be`` est
exact. Le siege belge (affaires commerciales, maladies rares) est a Zaventem.

Verifie le 2026-09-02 : 0 offre belge sur 95 dans le monde. Scraper pose quand
meme (comme BMS) — il remontera les offres des qu'il y en aura.
"""

from __future__ import annotations

from ananas.scrapers.registry import register
from ananas.scrapers.smartrecruiters import SmartRecruitersScraper


@register
class SobiScraper(SmartRecruitersScraper):
    key = "sobi-swedish-orphan-biovitrum"
    label = "Sobi – Swedish Orphan Biovitrum"
    sr_company = "Sobi"
    country = "be"
    careers_url = "https://jobs.smartrecruiters.com/Sobi"
