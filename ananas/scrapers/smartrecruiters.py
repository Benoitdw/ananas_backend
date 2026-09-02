"""Base pour les sites carrieres SmartRecruiters.

SmartRecruiters expose une **API publique et stable**, sans cle :

    GET https://api.smartrecruiters.com/v1/companies/{company}/postings
    GET https://api.smartrecruiters.com/v1/companies/{company}/postings/{id}

La liste accepte un filtre serveur ``country`` (code ISO 2 minuscules) — c'est
un filtre exact, pas une recherche de proximite. La fiche detaillee porte la
description en quatre sections HTML (``jobAd.sections``).

Sous-classer et definir ``key`` et ``company`` (l'identifiant SmartRecruiters,
visible dans l'URL ``jobs.smartrecruiters.com/<company>/...``).
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime
from typing import Any, ClassVar

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import html_to_text

log = logging.getLogger(__name__)

_API = "https://api.smartrecruiters.com/v1/companies"


class SmartRecruitersScraper(BaseScraper):
    """Sous-classer et definir ``key`` et ``company``."""

    # Identifiant SmartRecruiters de l'entreprise (casse respectee)
    company: ClassVar[str] = ""
    # Code pays ISO-3166 alpha-2, minuscules. Filtre serveur exact. "" = monde.
    country: ClassVar[str] = "be"
    # Jetons de ville retenus apres coup. Vide = on garde tout le pays.
    location_tokens: ClassVar[frozenset[str]] = frozenset()
    page_size: ClassVar[int] = 100
    max_pages: ClassVar[int] = 20
    rate_limit: ClassVar[float] = 0.25

    def fetch(self) -> list[JobPosting]:
        stubs = self._list()
        if self.location_tokens:
            toks = {t.casefold() for t in self.location_tokens}
            stubs = [
                s
                for s in stubs
                if any(t in _city(s).casefold() for t in toks)
            ]
        postings = [self._to_posting(s) for s in stubs]
        log.info("%s: %d offres (%s)", self.key, len(postings), self.country or "monde")
        return postings

    def _list(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for page in range(self.max_pages):
            params = {"limit": self.page_size, "offset": page * self.page_size}
            if self.country:
                params["country"] = self.country
            data = self._page(f"{_API}/{self.company}/postings", params)
            total = data.get("totalFound") or 0
            batch = data.get("content") or []
            if not batch:
                # SmartRecruiters repond parfois 200 + content vide sous
                # pression (throttling silencieux, pas de 429). Distinguer ce
                # cas d'un site reellement vide, sinon run() fermerait toutes
                # les offres du jour.
                if page == 0 and total > 0:
                    raise RuntimeError(
                        f"SmartRecruiters: {total} offres annoncees, 0 renvoyee "
                        "(throttling probable) — on reessaiera au prochain run"
                    )
                break
            out += batch
            if len(out) >= total:
                break
        return out

    def _page(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        """Une page de resultats, avec une reprise sur reponse vide."""
        for attempt in range(3):
            data = self.get_json(url, params=params)
            if data.get("content") or not (data.get("totalFound") or 0):
                return data
            time.sleep(1.5 * (attempt + 1))
        return data

    def _to_posting(self, stub: dict[str, Any]) -> JobPosting:
        detail = self._detail(stub["id"])
        sections = (detail.get("jobAd") or {}).get("sections") or {}
        description = "\n\n".join(
            html_to_text((sections.get(key) or {}).get("text") or "")
            for key in ("jobDescription", "qualifications", "additionalInformation")
        ).strip()
        return JobPosting(
            title=(stub.get("name") or "").strip(),
            url=detail.get("postingUrl")
            or f"https://jobs.smartrecruiters.com/{self.company}/{stub['id']}",
            location=_city(stub) or None,
            department=(stub.get("department") or {}).get("label") or None,
            description=description,
            posted_at=_as_date(stub.get("releasedDate")),
            # id numerique SmartRecruiters : stable d'un run a l'autre
            external_id=str(stub.get("id") or "") or None,
        )

    def _detail(self, posting_id: str) -> dict[str, Any]:
        try:
            return self.get_json(f"{_API}/{self.company}/postings/{posting_id}")
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: fiche %s illisible (%s)", self.key, posting_id, exc)
            return {}


def _city(stub: dict[str, Any]) -> str:
    loc = stub.get("location") or {}
    return loc.get("fullLocation") or loc.get("city") or ""


def _as_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None
