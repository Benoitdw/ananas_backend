"""Fonction publique federale belge — ``travaillerpour.be`` (Selor / BOSA).

Ce n'est pas un employeur mais le portail de recrutement de tous les services
publics federaux. La Liste An y suit deux recherches, chacune portee par une
fiche du repertoire:

- « Sciences, R&D » (domaine d'activite 139);
- un ensemble de sept domaines dont celui-ci (« toutes les offres » au sens
  de la liste).

Le site est un Drupal rendu cote serveur: la liste ``/fr/jobs?f[0]=...`` donne
des ``article.node--type-job``, paginee par ``&page=N`` (a partir de 0). Le
code de selection (``AFG26235``) ouvre l'URL de chaque fiche: c'est
l'identifiant public du recrutement, stable. La fiche donne le lieu de
travail et le texte complet.

Le filtre est dans ``careers_url``: corriger la recherche en base suffit, sans
redeployer.

Verifie le 2026-11-19: 2 offres (Sciences, R&D), 15 (sept domaines).
"""

from __future__ import annotations

import logging
import re
from typing import ClassVar
from urllib.parse import urljoin

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import txt
from ananas.scrapers.registry import register

log = logging.getLogger(__name__)

_CODE = re.compile(r"/jobs/([a-z]{3}\d+)-", re.IGNORECASE)


class TravaillerPourScraper(BaseScraper):
    """Sous-classer et definir ``key`` et ``careers_url`` (recherche filtree)."""

    max_pages: ClassVar[int] = 20
    rate_limit: ClassVar[float] = 0.4

    def fetch(self) -> list[JobPosting]:
        links: dict[str, str] = {}
        for page in range(self.max_pages):
            sep = "&" if "?" in self.careers_url else "?"
            soup = self.get_soup(f"{self.careers_url}{sep}page={page}")
            cards = soup.select("article.node--type-job")
            for card in cards:
                a = card.select_one(".node__title a[href]")
                if a and _CODE.search(a["href"]):
                    links.setdefault(urljoin(self.careers_url, a["href"]), txt(a))
            if not cards:
                break

        postings = [self._detail(url, title) for url, title in links.items()]
        log.info("%s: %d offres", self.key, len(postings))
        return postings

    def _detail(self, url: str, title: str) -> JobPosting:
        location, description = None, ""
        try:
            soup = self.get_soup(url)
            places = soup.select(".field--name-field-job-placesofemployment .field__item")
            location = ", ".join(dict.fromkeys(txt(p) for p in places)) or None
            body = soup.select_one("article.node--type-job") or soup.find("main")
            description = txt(body)[:8000] if body else ""
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: fiche %s illisible (%s)", self.key, url, exc)
        return JobPosting(
            title=title,
            url=url,
            location=location,
            description=description,
            external_id=_CODE.search(url).group(1).upper(),
        )


@register
class ServicesPublicsSciencesScraper(TravaillerPourScraper):
    key = "services-publiques-sciences-r-d"
    label = "Services publics - Sciences, R&D"
    careers_url = "https://travaillerpour.be/fr/jobs?f%5B0%5D=activitydomains%3A139&f%5B1%5D=lang%3Afr"


@register
class ServicesPublicsToutesOffresScraper(TravaillerPourScraper):
    key = "services-publiques-toutes-les-offres"
    label = "Services publics - Toutes les offres"
    careers_url = (
        "https://travaillerpour.be/fr/jobs?f%5B0%5D=activitydomains%3A112"
        "&f%5B1%5D=activitydomains%3A117&f%5B2%5D=activitydomains%3A130"
        "&f%5B3%5D=activitydomains%3A137&f%5B4%5D=activitydomains%3A138"
        "&f%5B5%5D=activitydomains%3A139&f%5B6%5D=activitydomains%3A144"
        "&f%5B7%5D=lang%3Afr"
    )
