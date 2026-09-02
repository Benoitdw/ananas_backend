"""Base pour les sites carrieres Workday (URL en ``*.myworkdayjobs.com``).

Workday equipe une bonne partie des grands groupes pharma (Pfizer, Novartis,
Bristol Myers Squibb, AstraZeneca, Baxter, Catalent…). Le site visible est
rendu en JavaScript, mais il est servi par une **API JSON publique et stable**,
la meme que consomme le front :

    POST {host}/wday/cxs/{tenant}/{site}/jobs      -> liste paginee
    GET  {host}/wday/cxs/{tenant}/{site}{path}     -> fiche complete

Aucun navigateur headless, aucun scraping de HTML.

Deux facons de restreindre a la Belgique, selon ce que le tenant expose :

1. **Facette pays** (``Location_Country``). Quand elle existe (Pfizer), c'est un
   filtre exact cote serveur : renseigner ``country_facet_wid`` et rien d'autre.
   Le WID se lit une fois via ``--probe`` (voir le bas du fichier) ou dans la
   reponse ``facets`` de l'API.
2. **Recherche texte + re-filtrage** (Novartis n'expose pas la facette). On
   envoie ``search_text = "Belgium"`` puis on ne garde que les fiches dont le
   ``country`` du JSON de detail est belge. La recherche texte de Workday
   matche aussi le lieu, mais elle peut laisser passer une annonce etrangere
   qui *mentionne* la Belgique : le re-filtrage sur ``countries`` la coupe.

Comme Sanofi (``sanofi.py``), le perimetre le plus fin reste le pays : ces
sites ne separent pas leurs implantations belges, et l'entreprise du repertoire
("Pfizer Belgium", "Novartis Pharma") est bien l'entite nationale.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, ClassVar

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import html_to_text

log = logging.getLogger(__name__)

# schema.org et Workday melangent code ISO et nom : on accepte les deux.
BELGIUM = frozenset({"BE", "BEL", "BELGIUM", "BELGIQUE", "BELGIE", "BELGIË"})


class WorkdayScraper(BaseScraper):
    """Sous-classer et definir ``key``, ``host``, ``tenant``, ``site``.
    Ne pas enregistrer cette classe : elle n'a pas de ``key``."""

    # Racine du site, ex. "https://pfizer.wd1.myworkdayjobs.com"
    host: ClassVar[str] = ""
    # Segment tenant dans le chemin CXS, ex. "pfizer"
    tenant: ClassVar[str] = ""
    # Identifiant du site carrieres, ex. "PfizerCareers"
    site: ClassVar[str] = ""
    # Nom de la facette pays, quasi toujours "Location_Country"
    country_facet: ClassVar[str] = "Location_Country"
    # WID de la valeur "Belgium" de cette facette. Vide -> pas de filtre facette.
    country_facet_wid: ClassVar[str] = ""
    # Texte de recherche, quand on ne filtre pas par facette
    search_text: ClassVar[str] = ""
    # Pays acceptes apres coup (re-filtrage sur le JSON de detail)
    countries: ClassVar[frozenset[str]] = BELGIUM
    # Pagination imposee par Workday
    page_size: ClassVar[int] = 20
    max_pages: ClassVar[int] = 25
    rate_limit: ClassVar[float] = 0.3

    # ------------------------------------------------------------ recuperation

    @property
    def _cxs(self) -> str:
        return f"{self.host.rstrip('/')}/wday/cxs/{self.tenant}/{self.site}"

    def fetch(self) -> list[JobPosting]:
        stubs = self._list()
        postings = [p for stub in stubs if (p := self._detail(stub))]

        if not self.countries:
            log.info("%s: %d offres", self.key, len(postings))
            return postings

        kept = [p for p in postings if p.raw.get("country") in self.countries]
        log.info(
            "%s: %d offres listees, %d retenues (%s)",
            self.key,
            len(postings),
            len(kept),
            "/".join(sorted(self.countries)),
        )
        if postings and not kept:
            # Un filtre qui rejette tout est plus probablement mal regle qu'un
            # site reellement vide : il faut que ça se voie.
            log.warning(
                "%s: aucune offre retenue. Pays vus : %s",
                self.key,
                sorted({p.raw.get("country", "?") for p in postings}),
            )
        return kept

    def _list(self) -> list[dict[str, Any]]:
        """Parcourt les pages de resultats jusqu'a epuisement."""
        facets: dict[str, list[str]] = {}
        if self.country_facet_wid:
            facets[self.country_facet] = [self.country_facet_wid]

        jobs: list[dict[str, Any]] = []
        seen: set[str] = set()

        for page in range(self.max_pages):
            data = self._post(
                f"{self._cxs}/jobs",
                {
                    "appliedFacets": facets,
                    "limit": self.page_size,
                    "offset": page * self.page_size,
                    "searchText": self.search_text,
                },
            )
            batch = data.get("jobPostings") or []
            if not batch:
                break

            new = 0
            for job in batch:
                path = job.get("externalPath")
                if path and path not in seen:
                    seen.add(path)
                    jobs.append(job)
                    new += 1

            total = data.get("total") or 0
            # `new` vide = la pagination se repete : on s'arrete plutot que de
            # tourner jusqu'a max_pages.
            if not new or len(jobs) >= total:
                break

        return jobs

    # ------------------------------------------------------------- conversion

    def _detail(self, stub: dict[str, Any]) -> JobPosting | None:
        """La fiche complete. Une fiche illisible est journalisee et ignoree,
        pas propagee : une offre cassee ne doit pas perdre tout le run."""
        url = f"{self._cxs}{stub['externalPath']}"
        try:
            info = (self._get(url) or {}).get("jobPostingInfo") or {}
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: fiche %s illisible (%s), ignoree", self.key, url, exc)
            return None

        country = (info.get("country") or {}).get("descriptor") or ""
        return JobPosting(
            title=(info.get("title") or stub.get("title") or "").strip(),
            url=info.get("externalUrl") or url,
            location=info.get("location") or stub.get("locationsText") or None,
            description=html_to_text(info.get("jobDescription") or ""),
            posted_at=_as_date(info.get("startDate")),
            # jobReqId : reference publique du poste, stable d'un run a l'autre
            # et affichee sur la fiche — survit a un changement de titre / slug.
            external_id=str(info.get("jobReqId") or "") or None,
            # `raw` ne participe pas au fingerprint : sert au re-filtrage pays.
            raw={"country": country.strip().upper()},
        )

    # ------------------------------------------------------------------- HTTP

    def _post(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        response = self.session.post(
            url, json=body, headers={"Accept": "application/json"}, timeout=30
        )
        response.raise_for_status()
        self.sleep()
        return response.json()

    def _get(self, url: str) -> dict[str, Any]:
        response = self.session.get(
            url, headers={"Accept": "application/json"}, timeout=30
        )
        response.raise_for_status()
        self.sleep()
        return response.json()


def _as_date(value: str | None) -> date | None:
    """Workday met "startDate" au format "2026-07-14"."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None
