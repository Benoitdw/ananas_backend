"""Base pour les sites carrieres Cegid Talentsoft.

Talentsoft equipe surtout des hopitaux et administrations belges. Comme les
sites Teamtailor/Joomla deja couverts (voir ``qbd_group.py``, ``qaelum.py``),
il expose un flux RSS complet — ``/handlers/offerRss.ashx?LCID=<locale>`` —
avec le HTML echappe de l'annonce dans ``<description>``. Verifie sans filtre
de categorie (``Rss_Contract``, ``Rss_EducationLevel``...): le flux "toutes
offres" suffit tant qu'on ne suit qu'un seul site par entreprise.

Piege observe (Cliniques Saint-Luc, 2026-09-08) : le flux ne porte ni
``<guid>`` ni lieu structure — l'identifiant stable est l'``idOffre`` de la
query string du lien, et le lieu se deduit du site unique de l'entreprise
(``town``), faute de mieux.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import date
from email.utils import parsedate_to_datetime
from typing import ClassVar

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import html_to_text

_OFFER_ID = re.compile(r"[?&]idOffre=(\d+)")


class TalentsoftScraper(BaseScraper):
    """Sous-classer et definir ``key``, ``base_url`` (et ``town``).

    Ne pas enregistrer cette classe: elle n'a pas de ``key``.
    """

    # Racine du site, ex. "https://jobs.saintluc.be"
    base_url: ClassVar[str] = ""
    # Code langue Talentsoft (LCID), 1036 = francais
    lcid: ClassVar[str] = "1036"
    # Localite unique de l'entreprise, faute de lieu structure dans le flux
    town: ClassVar[str] = ""
    rate_limit: ClassVar[float] = 0.4

    @property
    def feed_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/handlers/offerRss.ashx?LCID={self.lcid}"

    def fetch(self) -> list[JobPosting]:
        response = self.session.get(self.feed_url, timeout=30)
        response.raise_for_status()
        self.sleep()
        root = ET.fromstring(response.content)
        return [self._parse_item(item) for item in root.findall("./channel/item")]

    def _parse_item(self, item: ET.Element) -> JobPosting:
        url = (item.findtext("link") or "").strip()
        m = _OFFER_ID.search(url)
        return JobPosting(
            title=(item.findtext("title") or "").strip(),
            url=url,
            location=self.town or None,
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
