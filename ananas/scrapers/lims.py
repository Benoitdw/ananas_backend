"""LIMS-MBnext — Louvain-la-Neuve (laboratoire d'analyses medicales).

La page carrieres (WordPress/Elementor) aligne des boutons « Voir l'annonce »
vers des PDF ``wp-content/uploads/...``. Le titre de l'offre n'est que dans le
nom du fichier et dans le PDF: on le reconstruit depuis le nom de fichier
(``Annonce-IT-application-Specialist-.pdf`` -> « IT application Specialist »)
et le texte du PDF sert de description.

Verifie le 2026-11-19: 3 offres.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import unquote, urlsplit

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import pdf_text
from ananas.scrapers.registry import register

log = logging.getLogger(__name__)


@register
class LimsMBnextScraper(BaseScraper):
    key = "lims-mbnext"
    label = "LIMS-MBnext"
    careers_url = "https://lims-mbnext.eu/carrieres/"

    def fetch(self) -> list[JobPosting]:
        soup = self.get_soup(self.careers_url)
        urls = dict.fromkeys(
            self.absolutize(a["href"])
            for a in soup.select("a[href*='/wp-content/uploads/'][href$='.pdf']")
        )
        postings = [
            JobPosting(
                title=_title_from_file(url),
                url=url,
                location="Louvain-la-Neuve",
                description=pdf_text(url, sess=self.session),
            )
            for url in urls
        ]
        log.info("%s: %d offres", self.key, len(postings))
        return postings


def _title_from_file(url: str) -> str:
    name = unquote(urlsplit(url).path.rsplit("/", 1)[-1]).removesuffix(".pdf")
    name = re.sub(r"^Annonce[-_ ]*", "", name, flags=re.IGNORECASE)
    return re.sub(r"[-_]+", " ", name).strip().replace("Charge.e", "Chargé.e")
