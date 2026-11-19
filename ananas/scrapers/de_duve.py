"""Institut de Duve — Bruxelles (Woluwe). CMS Sanity, API publique.

Le site est un Next.js entierement rendu cote client (d'ou « Bloquee » dans
SCRAPERS.md au 2026-09-08). Mais son contenu vient d'un projet Sanity
(``b98ocrnx``, dataset ``production``) dont l'API de lecture est publique:
une requete GROQ sur les documents ``job`` donne titre, date, accroche et
l'annonce en PDF. ``_id`` est l'identifiant Sanity, stable.

Les textes sont multilingues (``[{_key: "en"|"fr"|"nl", value}]``): on prend le
francais, a defaut la premiere langue renseignee. Le texte du PDF sert de
description.

Verifie le 2026-11-19: 1 offre.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import pdf_text
from ananas.scrapers.registry import register

log = logging.getLogger(__name__)

PROJECT, DATASET = "b98ocrnx", "production"
QUERY = """*[_type == "job"] | order(datetime desc) {
  _id, datetime, title, description, location, slug,
  "pdfs": pdf[]{_key, "url": value.asset->url}
}"""


@register
class InstitutDeDuveScraper(BaseScraper):
    key = "institut-de-duve"
    label = "Institut de Duve"
    careers_url = "https://www.deduveinstitute.be/fr/jobs"

    def fetch(self) -> list[JobPosting]:
        data = self.get_json(
            f"https://{PROJECT}.apicdn.sanity.io/v2023-01-01/data/query/{DATASET}",
            params={"query": QUERY},
        )
        postings = [self._to_posting(job) for job in data.get("result") or []]
        log.info("%s: %d offres", self.key, len(postings))
        return postings

    def _to_posting(self, job: dict[str, Any]) -> JobPosting:
        pdf = _localized(job.get("pdfs"), key="url")
        summary = _localized(job.get("description"))
        return JobPosting(
            title=_localized(job.get("title")).strip(),
            # Pas de page par offre: l'annonce est le PDF.
            url=pdf or self.careers_url,
            location=_localized(job.get("location")) or "Bruxelles",
            description=(pdf_text(pdf, sess=self.session) if pdf else "") or summary,
            posted_at=_as_date(job.get("datetime")),
            external_id=job.get("_id") or None,
        )


def _localized(values: Any, key: str = "value", lang: str = "fr") -> str:
    """Valeur d'un tableau multilingue Sanity: ``lang``, sinon la premiere."""
    if isinstance(values, str):
        return values
    if not isinstance(values, list):
        return ""
    by_lang = {v.get("_key"): v.get(key) for v in values if isinstance(v, dict) and v.get(key)}
    return str(by_lang.get(lang) or next(iter(by_lang.values()), "") or "")


def _as_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None
