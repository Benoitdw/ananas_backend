"""Baxter — site carrieres Workday (`baxter.wd1`, site `baxter`).

Le portail public `jobs.baxter.com` (Radancy en vitrine) est alimente par ce
Workday. Au 2026-09-02 la facette pays de ce tenant ne liste **aucune** valeur
"Belgium" et ``searchText="Belgium"`` renvoie 0 — Baxter ne publie pas en
ligne les postes de Lessines / Braine-l'Alleud pour l'instant.

Le scraper est pose quand meme (comme BMS / Catalent) : il remontera les
offres belges des qu'il y en aura, sans intervention.
"""

from __future__ import annotations

from ananas.scrapers.registry import register
from ananas.scrapers.workday import WorkdayScraper


@register
class BaxterScraper(WorkdayScraper):
    key = "baxter"
    label = "Baxter"
    host = "https://baxter.wd1.myworkdayjobs.com"
    tenant = "baxter"
    site = "baxter"
    search_text = "Belgium"
    careers_url = "https://jobs.baxter.com/en"
