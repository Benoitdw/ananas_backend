"""KU Leuven — jobsite du personnel (``kuleuven.be/personeel/jobsite``).

La page ``/jobs/staff`` est une coquille: un composant Vue (« filter2 » de
l'ICTS KU Leuven) interroge un Elasticsearch via
``POST <api>/api/projects/Jobsite_academic/search?<query de la page>``. La
query string de la page (``12=["Biology",...]``, ``page=N``) est transmise
telle quelle a l'API: **les filtres vivent dans ``careers_url``**. Corriger la
recherche en base suffit, sans redeployer. Le parametre ``page`` de l'URL est
ignore: on parcourt toutes les pages (15 offres par page).

Chaque resultat ne donne que titre, accroche, unite et date limite; la fiche
``/jobs/<id>`` est rendue cote serveur et donne le texte complet.

Verifie le 2026-11-25: 13 offres avec les filtres de la Liste An (facette 12:
Cellular and Molecular Medicine, Science, Pharmaceutical & Pharmacological
Sciences, Oncology, Neurosciences, Research professor (BOFZAP), Biology), 53
sans filtre.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import ClassVar
from urllib.parse import parse_qsl, urlencode, urlsplit

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import txt
from ananas.scrapers.registry import register

log = logging.getLogger(__name__)

API = "https://icts-p-fii-toep-component-filter2.cloud.icts.kuleuven.be/api/projects"
DETAIL = "https://www.kuleuven.be/personeel/jobsite/jobs/{id}?lang=en"


def _search_query(careers_url: str, page: int) -> str:
    """Query string de la page carrieres, ``page`` remplace."""
    params = [(k, v) for k, v in parse_qsl(urlsplit(careers_url).query) if k != "page"]
    params.append(("page", str(page)))
    return urlencode(params)


def _apply_before(value: str | None) -> str:
    try:
        return datetime.strptime(value or "", "%Y%m%d").date().isoformat()
    except ValueError:
        return ""


@register
class KuLeuvenScraper(BaseScraper):
    key = "ku-leuven"
    label = "KU Leuven"
    careers_url = (
        "https://www.kuleuven.be/personeel/jobsite/jobs/staff?12=%5B%22Cellular%20and%20Molecular"
        "%20Medicine%22,%22Science%22,%22Pharmaceutical%20%26%20Pharmacological%20Sciences%22,"
        "%22Oncology%22,%22Neurosciences%22,%22Research%20professor%20%28BOFZAP%29%22,"
        "%22Biology%22%5D&hl=en&lang=en&page=0"
    )
    project: ClassVar[str] = "Jobsite_academic"
    max_pages: ClassVar[int] = 30

    def fetch(self) -> list[JobPosting]:
        hits: list[dict] = []
        for page in range(self.max_pages):
            r = self.session.post(
                f"{API}/{self.project}/search?{_search_query(self.careers_url, page)}",
                json={"_locale": "en", "environment": "production", "release": ""},
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            batch = data.get("hits") or []
            hits.extend(batch)
            self.sleep()
            if not batch or len(hits) >= data.get("total_nb_hits", 0):
                break

        postings = [self._posting(h.get("_source") or {}) for h in hits]
        postings = [p for p in postings if p]
        log.info("%s: %d offres", self.key, len(postings))
        return postings

    def _posting(self, src: dict) -> JobPosting | None:
        job_id = str(src.get("id") or "").strip()
        title = ((src.get("posting") or {}).get("title") or "").strip()
        if not job_id or not title:
            return None
        url = DETAIL.format(id=job_id)
        unit = src.get("orgUnitDescription") or None
        teaser = (src.get("posting") or {}).get("teaser") or ""
        description = self._description(url) or teaser
        deadline = _apply_before(src.get("applyBefore"))
        if deadline:
            description = f"Apply before: {deadline}\n\n{description}"
        return JobPosting(
            title=title,
            url=url,
            location=src.get("city") or "Leuven",
            description=description[:8000],
            department=unit,
            external_id=job_id,
            raw=src,
        )

    def _description(self, url: str) -> str:
        try:
            soup = self.get_soup(url)
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: fiche %s illisible (%s)", self.key, url, exc)
            return ""
        body = soup.select_one(".col-md-8")
        return txt(body)

