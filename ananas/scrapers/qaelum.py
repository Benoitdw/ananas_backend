"""Qaelum — Leuven. Section carrieres Joomla avec flux RSS.

``/about-us/career?format=feed&type=rss`` expose les offres en RSS 2.0 (titre,
lien, date, resume HTML). On prend la description complete sur la fiche. Siege
unique en Belgique.

Verifie le 2026-09-02 : 1 offre (Chief Financial Officer).
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import date
from email.utils import parsedate_to_datetime

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import html_to_text, txt
from ananas.scrapers.registry import register

log = logging.getLogger(__name__)


@register
class QaelumScraper(BaseScraper):
    key = "qaelum"
    label = "Qaelum"
    feed_url = "https://qaelum.com/about-us/career?format=feed&type=rss"
    careers_url = "https://qaelum.com/about-us/career"
    rate_limit = 0.3

    def fetch(self) -> list[JobPosting]:
        response = self.session.get(self.feed_url, timeout=30)
        response.raise_for_status()
        self.sleep()
        root = ET.fromstring(response.content)

        postings = []
        for item in root.findall("./channel/item"):
            url = (item.findtext("link") or "").strip()
            postings.append(
                JobPosting(
                    title=(item.findtext("title") or "").strip(),
                    url=url,
                    location="Leuven",
                    description=self._description(url)
                    or html_to_text(item.findtext("description") or ""),
                    posted_at=_as_date(item.findtext("pubDate")),
                    external_id=(item.findtext("guid") or url).strip() or None,
                )
            )
        log.info("%s: %d offres", self.key, len(postings))
        return postings

    def _description(self, url: str) -> str:
        if not url:
            return ""
        try:
            soup = self.get_soup(url)
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: fiche %s illisible (%s)", self.key, url, exc)
            return ""
        body = soup.select_one(".item-page, article, main, .content")
        return txt(body)[:8000] if body else ""


def _as_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return parsedate_to_datetime(raw).date()
    except (TypeError, ValueError):
        return None
