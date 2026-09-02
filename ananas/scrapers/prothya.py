"""Prothya Biosolutions (ex-Sanquin Plasma Products) — Bruxelles.

Site carrieres belge propre (``careers-be.prothya.com``, WordPress). Il n'y a
pas de page « toutes les offres » exploitable : l'accueil liste les
**departements**, et chaque page departement liste ses offres sous forme de
liens ``/vacancy/?jobCode=<code>``. On parcourt donc les departements et on
dedoublonne (une offre peut apparaitre sous deux departements).

``jobCode`` est la reference interne du poste : stable, on s'en sert comme
``external_id``. Toutes les offres sont a Bruxelles (site unique).

Verifie le 2026-09-02 : 15 offres.
"""

from __future__ import annotations

import logging
from typing import ClassVar
from urllib.parse import urljoin

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import txt
from ananas.scrapers.registry import register

log = logging.getLogger(__name__)


@register
class ProthyaScraper(BaseScraper):
    key = "prothya-biosolutions"
    label = "Prothya Biosolutions"
    base_url: ClassVar[str] = "https://careers-be.prothya.com"
    careers_url = "https://careers-be.prothya.com/"
    rate_limit = 0.3

    def fetch(self) -> list[JobPosting]:
        home = self.get_soup(self.careers_url)
        depts = sorted(
            {
                urljoin(self.base_url, a["href"])
                for a in home.select("a[href*='/department-vacancies/']")
                # les variantes /nl/ et /fr/ pointent sur les memes offres
                if "/nl/" not in a["href"] and "/fr/" not in a["href"]
            }
        )
        if not depts:
            raise ValueError("aucun departement trouve sur la page carrieres Prothya")

        seen: dict[str, JobPosting] = {}
        for url in depts:
            soup = self.get_soup(url)
            for a in soup.select("a[href*='jobCode=']"):
                href = urljoin(self.base_url, a["href"])
                code = href.split("jobCode=", 1)[1].split("&")[0]
                if code in seen:
                    continue
                label = txt(a)
                # "Titre | precision | Bruxelles | 4 days/week" : le lieu peut
                # etre au milieu. On l'extrait par mot-cle (site unique), le
                # reste fait le titre.
                parts = [p.strip() for p in label.split("|") if p.strip()]
                loc = next(
                    (p for p in parts if p.casefold().startswith("brus")), "Brussels"
                )
                title = " | ".join(p for p in parts if p != loc) or label
                seen[code] = JobPosting(
                    title=title,
                    url=href,
                    location=loc,
                    description=self._description(href),
                    external_id=code,
                )

        log.info("%s: %d offres (%d departements)", self.key, len(seen), len(depts))
        return list(seen.values())

    def _description(self, url: str) -> str:
        try:
            soup = self.get_soup(url)
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: fiche %s illisible (%s)", self.key, url, exc)
            return ""
        main = soup.select_one("div.vacancy, main")
        return txt(main)[:8000] if main else ""
