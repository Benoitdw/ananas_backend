"""Pages carrieres sans offre en ligne au 2026-11-19: veille de l'etat vide.

Voir ``page_watch.py``. Chaque page affiche aujourd'hui une phrase explicite
« aucune offre »; tant qu'elle y est, 0 offre. Si elle disparait, une offre
« nouvelle(s) offre(s) sur la page carrieres » est remontee — c'est le signal
pour ecrire le vrai parseur.

Ajoutes pour la Liste An. Les phrases sont recopiees telles quelles des pages.
"""

from __future__ import annotations

from ananas.scrapers.page_watch import PageWatchScraper
from ananas.scrapers.registry import register


@register
class ChemoSensoryXScraper(PageWatchScraper):
    key = "chemosensoryx"
    label = "ChemoSensoryX"
    careers_url = "http://chemosensoryx.be/news/jobs/"
    empty_markers = ("there are no positions available at this time",)


@register
class One2TreatScraper(PageWatchScraper):
    key = "one2treat"
    label = "One2Treat"
    careers_url = "https://one2treat.com/careers/"
    empty_markers = ("Currently no open positions",)


@register
class AbolerisPharmaScraper(PageWatchScraper):
    key = "aboleris-pharma"
    label = "AbolerIS Pharma"
    careers_url = "https://aboleris-pharma.com/career/"
    empty_markers = ("There are currently no open vacancies",)


@register
class TwoBridgeScraper(PageWatchScraper):
    """Sans offre, l'onglet « Job opportunity » de /career/#positions ne
    contient que son titre et le formulaire de candidature spontanee: c'est
    tout autre contenu que l'on guette."""

    key = "2-bridge"
    label = "2 Bridge"
    careers_url = "https://2bridge.be/career/"
    region = "#tab-job-opportunity"

    def is_empty(self, zone) -> bool:
        for form in zone.select("form"):
            form.decompose()
        return zone.get_text(" ", strip=True).casefold() in {"", "job opportunities"}


@register
class CMMIScraper(PageWatchScraper):
    key = "center-for-microscopy-and-molecular-imaging-cmmi"
    label = "CMMI"
    careers_url = "https://www.cmmi.be/join-us"
    empty_markers = ("Coming soon",)
