"""Croix-Rouge de Belgique (Communaute francophone) — Wallonie et Bruxelles.

``jobs.croix-rouge.be/offres-emploi/`` (WordPress) accepte des filtres de
secteur en parametre (``?secteur=administration,sante-et-paramedical,...``):
la recherche de la Liste An est dans ``careers_url``. Chaque offre est un lien
``/jobs/<slug>-<id>/``, ``<id>`` etant l'identifiant WordPress de l'offre.

Distincte de la fiche BioWin « Croix rouge de Belgique - Service du sang »,
qui ne couvre que le service du sang.

Verifie le 2026-11-19: 11 offres sur les secteurs suivis.
"""

from __future__ import annotations

import html as html_mod
import logging
import re

from bs4 import BeautifulSoup

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import html_to_text, jsonld_job_posting, txt
from ananas.scrapers.registry import register

log = logging.getLogger(__name__)

_JOB = re.compile(r"/jobs/[a-z0-9-]+-(\d+)/?$")


@register
class CroixRougeScraper(BaseScraper):
    key = "croix-rouge-de-belgique"
    label = "Croix-Rouge de Belgique"
    careers_url = (
        "https://jobs.croix-rouge.be/offres-emploi/?secteur=administration,"
        "sante-et-paramedical,activites-internationales,gestion-de-projet,management"
    )
    rate_limit = 0.4

    def fetch(self) -> list[JobPosting]:
        soup = self.get_soup(self.careers_url)
        links: dict[str, str] = {}
        for a in soup.select("a[href*='/jobs/']"):
            url = self.absolutize(a["href"])
            if _JOB.search(url):
                links.setdefault(url, a)
        postings = [self._detail(url, a) for url, a in links.items()]
        log.info("%s: %d offres", self.key, len(postings))
        return postings

    def _detail(self, url: str, card) -> JobPosting:
        heading = card.select_one("h2, h3, h4, .title, [class*=title]")
        title = txt(heading) or txt(card)
        description, location = "", None
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            self.sleep()
            ld = jsonld_job_posting(response.text)
            if ld:
                title = (ld.get("title") or "").strip() or title
                description = html_to_text(html_mod.unescape(ld.get("description") or ""))
            if not description:
                page = BeautifulSoup(response.text, "html.parser")
                for node in page(["script", "style", "nav", "header", "footer", "noscript"]):
                    node.decompose()
                h1 = page.find("h1")
                title = txt(h1) or title
                description = txt(page.find("main") or page.body)[:8000]
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: fiche %s illisible (%s)", self.key, url, exc)
        return JobPosting(
            title=title,
            url=url,
            location=location,
            description=description,
            external_id=_JOB.search(url).group(1),
        )
