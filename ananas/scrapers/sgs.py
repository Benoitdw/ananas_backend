"""SGS Belgium — dont SGS Lab Simon (Wavre/Bierges). API SmartRecruiters ``SGS``.

Le site ``sgs.com`` (Next.js) affiche les offres SmartRecruiters du groupe.
L'API publique accepte le filtre exact ``country=be`` — c'est ce qui manquait
dans SCRAPERS.md (« Workday sgs.wd3 repond 401 »): le Workday n'est pas la
source publique, SmartRecruiters l'est.

Perimetre: toute la Belgique (Anvers, Wavre, Melsele...). La fiche du
repertoire est SGS Lab Simon (Bierges, commune de Wavre); filtrer sur Wavre
seul ferait perdre les postes des autres laboratoires belges, que la Liste An
vise (« SGS — Wavre » avec la recherche pays Belgique).

Verifie le 2026-11-19: 52 offres en Belgique.
"""

from __future__ import annotations

from ananas.scrapers.registry import register
from ananas.scrapers.smartrecruiters import SmartRecruitersScraper


@register
class SGSScraper(SmartRecruitersScraper):
    key = "sgs-lab-simon"
    label = "SGS Belgium"
    sr_company = "SGS"
    country = "be"
    careers_url = (
        "https://www.sgs.com/fr-be/notre-entreprise/carrieres-chez-sgs/offres-d-emploi"
        "?Location=Belgium"
    )
