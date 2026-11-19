"""Base pour les sites carrieres SAP SuccessFactors "ancien theme" (moteur
jobs2web / Career Site Builder), tels qu'utilises par UCLouvain.

Contrairement au theme recent deja couvert par ``successfactors.py`` (liste
HTML rendue cote serveur), ce theme expose en plus un **flux RSS par
categorie**: ``/services/rss/category/?catid=<id>``. C'est la source la plus
robuste — l'annonce complete y est deja embarquee en HTML echappe, pas besoin
d'ouvrir chaque fiche.

Une "categorie" correspond a un regroupement de postes decide par le site
(ex. UCLouvain distingue personnel administratif / scientifique / academique,
chacune avec son propre ``catid``): une entreprise avec plusieurs categories
suivies = une sous-classe par categorie, meme ``base_url``.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import date
from email.utils import parsedate_to_datetime
from typing import ClassVar

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import html_to_text

# "/go/<slug>/<id>/" ou "/job/<slug>/<id>/" — l'identifiant numerique final
# est la reference SuccessFactors, stable malgre un changement de titre.
_JOB_ID = re.compile(r"/(\d+)/?(?:\?|$)")


class Jobs2WebScraper(BaseScraper):
    """Sous-classer et definir ``key``, ``base_url``, ``category_id``.

    Ne pas enregistrer cette classe: elle n'a pas de ``key``.
    """

    # Racine du site, ex. "https://jobs.uclouvain.be"
    base_url: ClassVar[str] = ""
    # Identifiant numerique de la categorie (``catid`` dans l'URL du flux)
    category_id: ClassVar[str] = ""
    rate_limit: ClassVar[float] = 0.4

    @property
    def feed_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/services/rss/category/?catid={self.category_id}"

    def fetch(self) -> list[JobPosting]:
        response = self.session.get(self.feed_url, timeout=30)
        response.raise_for_status()
        self.sleep()
        root = ET.fromstring(response.content)
        # Une categorie vide publie un item factice « Aucune offre d'emploi
        # actuellement disponible » qui pointe vers la racine du site: sans
        # identifiant d'offre, ce n'est pas une offre.
        return [
            self._parse_item(item)
            for item in root.findall("./channel/item")
            if _JOB_ID.search(item.findtext("link") or "")
        ]

    def _parse_item(self, item: ET.Element) -> JobPosting:
        url = (item.findtext("link") or "").strip()
        m = _JOB_ID.search(url)
        return JobPosting(
            title=(item.findtext("title") or "").strip(),
            url=url,
            description=html_to_text(item.findtext("description") or ""),
            posted_at=_as_date(item.findtext("pubDate")),
            external_id=m.group(1) if m else None,
        )


def _as_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return parsedate_to_datetime(raw).date()
    except (TypeError, ValueError):
        return None
