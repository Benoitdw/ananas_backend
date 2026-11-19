"""IPG (Institut de Pathologie et de Genetique) et sa filiale Seqalis — Gosselies.

``jobs.ipg.be`` est un habillage du site carrieres TalentSquare ``ipg``. Seqalis
n'a pas de recrutement propre: sa page carrieres renvoie explicitement vers
``jobs.ipg.be``. Le scraper Seqalis lit donc le meme flux et ne garde que les
offres qui mentionnent Seqalis (titre ou description) — les autres restent
sous IPG.

Verifie le 2026-11-19: 4 offres IPG, aucune ne mentionnant Seqalis.
"""

from __future__ import annotations

from ananas.scrapers.base import JobPosting
from ananas.scrapers.registry import register
from ananas.scrapers.talentsquare import TalentSquareScraper


@register
class IPGScraper(TalentSquareScraper):
    key = "institute-of-pathology-and-genetics-ipg"
    label = "IPG"
    ts_slug = "ipg"
    careers_url = "https://jobs.ipg.be/careers/searchjobs"


@register
class SeqalisScraper(TalentSquareScraper):
    key = "seqalis"
    label = "Seqalis"
    ts_slug = "ipg"
    careers_url = "https://jobs.ipg.be/careers/searchjobs"

    def fetch(self) -> list[JobPosting]:
        return [
            p
            for p in super().fetch()
            if "seqalis" in f"{p.title} {p.description or ''}".casefold()
        ]
