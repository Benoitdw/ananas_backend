"""Scraper d'exemple — QbD Group, via son site carrieres Teamtailor.

Sert de gabarit pour les scrapers ecrits a la main. Deux choses a en retenir:

1. **Chercher un flux structure avant de parser du HTML.** QbD publie ses
   offres sur careers.qbdgroup.com (Teamtailor), qui expose un RSS a
   ``/jobs.rss``. Un flux survit aux refontes graphiques, contrairement a des
   selecteurs CSS. Reflexe a avoir aussi pour Greenhouse (``/embed/job_board``),
   Lever (``api.lever.co/v0/postings/...``), Recruitee (``/api/offers/``),
   Workable, SmartRecruiters — tous ont un endpoint public.

2. **Factoriser par ATS, pas par entreprise.** ``TeamtailorScraper`` contient
   toute la logique; brancher une autre entreprise Teamtailor ne coute que
   trois lignes (voir QbDGroupScraper en bas de fichier).

Verifie le 2026-09-02: 36 offres, un ``guid`` stable sur chacune.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date
from email.utils import parsedate_to_datetime
from typing import ClassVar

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.registry import register

# Namespace des extensions Teamtailor dans le flux RSS
TT_NS = {"tt": "https://teamtailor.com/locations"}


class TeamtailorScraper(BaseScraper):
    """Base pour toute entreprise hebergee sur Teamtailor.

    Ne pas enregistrer cette classe: elle est abstraite au sens du registre
    (pas de ``key``). Sous-classer et definir ``key`` + ``base_url``.
    """

    # Racine du site carrieres, ex. "https://careers.qbdgroup.com"
    base_url: ClassVar[str] = ""

    @property
    def feed_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/jobs.rss"

    def fetch(self) -> list[JobPosting]:
        response = self.session.get(self.feed_url, timeout=30)
        response.raise_for_status()
        self.sleep()

        # On parse les octets bruts: laisser ElementTree lire l'encodage
        # declare dans le prologue XML evite de casser les accents.
        root = ET.fromstring(response.content)

        return [self._parse_item(item) for item in root.findall("./channel/item")]

    def _parse_item(self, item: ET.Element) -> JobPosting:
        return JobPosting(
            title=(item.findtext("title") or "").strip(),
            url=(item.findtext("link") or "").strip(),
            location=self._location(item),
            description=self._department(item),
            posted_at=self._published(item),
            # Le guid Teamtailor est un UUID stable: il survit a un changement
            # de titre ou de slug d'URL, contrairement au fingerprint calcule.
            external_id=(item.findtext("guid") or "").strip() or None,
        )

    @staticmethod
    def _location(item: ET.Element) -> str | None:
        """Une offre peut etre ouverte sur plusieurs sites; on les concatene."""
        names = [
            n.text.strip()
            for n in item.findall("tt:locations/tt:location/tt:name", TT_NS)
            if n.text and n.text.strip()
        ]
        # dict.fromkeys: dedoublonne en gardant l'ordre d'apparition
        return ", ".join(dict.fromkeys(names)) or None

    @staticmethod
    def _department(item: ET.Element) -> str | None:
        dep = item.findtext("tt:department", namespaces=TT_NS)
        return dep.strip() if dep and dep.strip() else None

    @staticmethod
    def _published(item: ET.Element) -> date | None:
        raw = item.findtext("pubDate")
        if not raw:
            return None
        try:
            return parsedate_to_datetime(raw).date()
        except (TypeError, ValueError):
            # Une date mal formee ne doit pas faire echouer tout le scrape
            return None


@register
class QbDGroupScraper(TeamtailorScraper):
    key = "qbd-group"
    label = "QbD Group"
    base_url = "https://careers.qbdgroup.com"
    careers_url = "https://careers.qbdgroup.com/jobs"
