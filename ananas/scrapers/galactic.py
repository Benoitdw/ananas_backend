"""Galactic — Bruxelles. ATS TalentFinder (``galactic.talentfinder.be``).

TalentFinder est un ATS belge. La page ``/en/vacatures/index.aspx`` liste les
offres (liens ``/en/vacature/<id>/<slug>/``) ; chaque fiche publie un bloc
**schema.org JobPosting** en JSON-LD — titre, date, lieu, description, id
stable (``JobID``). On s'appuie dessus plutot que sur des selecteurs CSS.

Verifie le 2026-09-02 : 1 offre (Bruxelles).
"""

from __future__ import annotations

import html as html_mod
import logging
import re
from datetime import date, datetime
from typing import Any
from urllib.parse import urljoin

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import html_to_text, jsonld_job_posting
from ananas.scrapers.registry import register

log = logging.getLogger(__name__)

_VACATURE = re.compile(r"/vacature/\d+/")


@register
class GalacticScraper(BaseScraper):
    key = "galactic"
    label = "Galactic"
    base_url = "https://galactic.talentfinder.be"
    careers_url = "https://galactic.talentfinder.be/en/vacatures/index.aspx"
    rate_limit = 0.4

    def fetch(self) -> list[JobPosting]:
        soup = self.get_soup(self.careers_url)
        urls = sorted(
            {
                urljoin(self.base_url, a["href"])
                for a in soup.select("a[href*='/vacature/']")
                if _VACATURE.search(a["href"])
            }
        )
        postings = [p for url in urls if (p := self._detail(url))]
        log.info("%s: %d offres", self.key, len(postings))
        return postings

    def _detail(self, url: str) -> JobPosting | None:
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            self.sleep()
            ld = jsonld_job_posting(response.text)
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: fiche %s illisible (%s)", self.key, url, exc)
            return None
        if not ld:
            return None
        return JobPosting(
            title=(ld.get("title") or "").strip(),
            url=url,
            location=_place(ld.get("jobLocation")),
            description=html_to_text(html_mod.unescape(ld.get("description") or "")),
            posted_at=_as_date(ld.get("datePosted")),
            external_id=_identifier(ld) or _VACATURE.search(url).group(0).strip("/").split("/")[-1],
        )


def _place(node: Any) -> str | None:
    node = node[0] if isinstance(node, list) and node else node
    address = (node or {}).get("address") or {}
    parts = [address.get("addressLocality"), address.get("addressCountry")]
    return ", ".join(p for p in parts if p) or None


def _identifier(ld: dict[str, Any]) -> str | None:
    ident = ld.get("identifier")
    if isinstance(ident, dict):
        return str(ident.get("value") or "") or None
    return str(ident) if ident else None


def _as_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None
