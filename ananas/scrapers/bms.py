"""Bristol Myers Squibb Belgium — site carrieres Workday.

Ce tenant n'expose **aucune** facette pays : on passe par la recherche texte
(``search_text = "Belgium"``) puis on re-filtre sur le ``country`` du JSON de
detail.

Limite connue : si BMS publie un poste a Braine-l'Alleud sans "Belgium" dans
le libelle de lieu, la recherche texte ne le verra pas. C'est le meilleur
compromis tant que le site n'offre pas de filtre pays.

Verifie le 2026-09-02 : 0 offre belge (le scraper est valide, il remontera
les offres des qu'il y en aura).
"""

from __future__ import annotations

from ananas.scrapers.registry import register
from ananas.scrapers.workday import WorkdayScraper


@register
class BristolMyersSquibbScraper(WorkdayScraper):
    key = "bristol-myers-squibb"
    label = "Bristol Myers Squibb"
    host = "https://bristolmyerssquibb.wd5.myworkdayjobs.com"
    tenant = "bristolmyerssquibb"
    site = "BMS"
    search_text = "Belgium"
    careers_url = "https://bristolmyerssquibb.wd5.myworkdayjobs.com/BMS"
