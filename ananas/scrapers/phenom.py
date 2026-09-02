"""Base pour les sites carrieres Phenom People.

Phenom equipe beaucoup de grands groupes (GSK, Sanofi, UCB…). Ces sites sont
rendus en JavaScript, mais le serveur embarque l'etat initial dans un objet
``phApp.ddo`` : on y trouve les resultats de recherche complets, sans avoir a
piloter un navigateur.

Trois pieges specifiques a Phenom, tous traites ici :

1. **Chaque instance filtre les lieux a sa facon.** GSK accepte
   ``m=3&location=<ville>``, une recherche de *proximite*; UCB ignore ce
   parametre et attend ``qcity/qstate/qcountry``, un filtre exact. D'ou
   ``search_params``, un dictionnaire libre que chaque sous-classe fournit.
2. **La recherche de proximite n'est pas un filtre.** Interroger "Rixensart"
   renvoie aussi des postes a Londres ou Collegeville. ``town`` sert donc au
   filtrage effectif, sur ``multi_location`` — un poste ouvert a la fois a
   Londres et a Rixensart est legitimement retenu, ce que le champ ``city``
   seul ferait manquer.
3. **La liste ne contient qu'un extrait de description.** L'annonce complete
   n'est que sur la fiche, qu'il faut donc ouvrir une par une.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime
from typing import Any, ClassVar
from urllib.parse import quote

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import html_to_text

log = logging.getLogger(__name__)

# `phApp.ddo = {...}` : on decode a partir de l'accolade plutot que par une
# expression reguliere, le JSON contenant lui-meme des accolades.
_DDO_ANCHOR = re.compile(r"phApp\.ddo\s*=\s*")

# Correspondances des libelles Phenom vers le vocabulaire d'Ananas
REMOTE = {
    "sur site": "sur_site",
    "on-site": "sur_site",
    "hybride": "hybride",
    "hybrid": "hybride",
    "a distance": "distanciel",
    "remote": "distanciel",
}


class PhenomScraper(BaseScraper):
    """Sous-classer et definir ``key``, ``base_url``, ``search_params`` et
    ``town``. Ne pas enregistrer cette classe: elle n'a pas de ``key``."""

    # Racine du site, ex. "https://jobs.gsk.com"
    base_url: ClassVar[str] = ""
    # Segment de langue du site, ex. "be/fr"
    locale_path: ClassVar[str] = ""
    # Parametres de recherche, propres a chaque instance Phenom (voir piege 1).
    # Ex. {"m": "3", "location": "Wavre, Brabant wallon, Belgique"}
    #  ou {"qcity": "Anderlecht", "qstate": "Brussels", "qcountry": "Belgium"}
    search_params: ClassVar[dict[str, str]] = {}
    # Ville a conserver apres coup (voir le piege 2)
    town: ClassVar[str] = ""
    # Jetons de lieu supplementaires (nom de pays typiquement). Utile quand la
    # recherche par ville est trop etroite ou absente et qu'on veut retenir
    # tout poste ouvert dans le pays — MSD, Roche : leur ``multi_location``
    # porte "..., Belgium" sur chaque site belge. Vide = on s'en tient a `town`.
    location_tokens: ClassVar[frozenset[str]] = frozenset()
    # Nombre de resultats par page, impose par le site
    page_size: ClassVar[int] = 10
    # Garde-fou: au-dela, on considere que la pagination boucle
    max_pages: ClassVar[int] = 30
    rate_limit: ClassVar[float] = 0.4

    # ------------------------------------------------------------ recuperation

    def fetch(self) -> list[JobPosting]:
        raw = self._search()
        kept = [job for job in raw if self._is_local(job)]
        log.info(
            "%s: %d offres renvoyees par la recherche, %d retenues pour %s",
            self.key,
            len(raw),
            len(kept),
            self.town,
        )
        return [self._to_posting(job) for job in kept]

    def _search(self) -> list[dict[str, Any]]:
        """Parcourt les pages de resultats jusqu'a epuisement."""
        jobs: list[dict[str, Any]] = []
        seen: set[str] = set()

        for page in range(self.max_pages):
            data = self._ddo(self._search_url(page * self.page_size))
            block = data.get("eagerLoadRefineSearch") or {}
            batch = (block.get("data") or {}).get("jobs") or []
            if not batch:
                break

            new = [j for j in batch if j.get("jobId") not in seen]
            seen.update(j.get("jobId") for j in batch)
            jobs += new

            total = block.get("totalHits") or 0
            # `new` vide = la pagination se repete: on s'arrete plutot que de
            # tourner jusqu'a max_pages.
            if not new or len(jobs) >= total:
                break

        return jobs

    def _search_url(self, offset: int) -> str:
        base = f"{self.base_url.rstrip('/')}/{self.locale_path.strip('/')}/search-results"
        params = {**self.search_params, "from": str(offset)}
        query = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
        return f"{base}?{query}"

    def _ddo(self, url: str) -> dict[str, Any]:
        """Etat initial embarque dans la page."""
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        self.sleep()

        match = _DDO_ANCHOR.search(response.text)
        if not match:
            raise ValueError(f"phApp.ddo introuvable sur {url}")

        # raw_decode s'arrete a la fin de l'objet: robuste a ce qui suit.
        data, _ = json.JSONDecoder().raw_decode(response.text[match.end() :])
        return data

    # -------------------------------------------------------------- filtrage

    def _is_local(self, job: dict[str, Any]) -> bool:
        """Un des lieux du poste correspond-il au perimetre voulu ?

        On regarde ``multi_location`` et non ``city``: un poste ouvert a la
        fois a Londres et a Rixensart porte ``city = London`` mais concerne
        bien le site local. Le perimetre est ``town`` et/ou ``location_tokens``
        (nom de pays) ; sans aucun des deux, tout est retenu.
        """
        needles = {self.town.casefold()} if self.town else set()
        needles |= {tok.casefold() for tok in self.location_tokens}
        if not needles:
            return True
        places = job.get("multi_location") or [job.get("location", "")]
        return any(n in (place or "").casefold() for place in places for n in needles)

    # ------------------------------------------------------------ conversion

    def _to_posting(self, job: dict[str, Any]) -> JobPosting:
        url = self._job_url(job)
        return JobPosting(
            title=(job.get("title") or "").strip(),
            url=url,
            location=_places(job),
            department=(job.get("category") or None),
            description=self._description(url, job),
            posted_at=_as_date(job.get("postedDate") or job.get("dateCreated")),
            # jobId est l'identifiant interne du poste: il survit a un
            # changement de titre ou de slug d'URL.
            external_id=str(job.get("jobId") or "") or None,
        )

    def _job_url(self, job: dict[str, Any]) -> str:
        slug = re.sub(r"[^A-Za-z0-9]+", "-", job.get("title") or "poste").strip("-")[:80]
        return (
            f"{self.base_url.rstrip('/')}/{self.locale_path.strip('/')}"
            f"/job/{job.get('jobSeqNo')}/{quote(slug)}"
        )

    def _description(self, url: str, job: dict[str, Any]) -> str:
        """Annonce complete depuis la fiche; l'extrait de la liste en secours.

        Une fiche indisponible ne doit pas faire perdre l'offre: on garde
        l'extrait, quitte a caracteriser l'offre moins finement.
        """
        try:
            detail = self._ddo(url)
            html = ((detail.get("jobDetail") or {}).get("data") or {}).get("job", {}).get(
                "description", ""
            )
            if text := html_to_text(html):
                return text
        except Exception as exc:  # noqa: BLE001
            log.warning("fiche %s illisible (%s), repli sur l'extrait", url, exc)

        parts = [
            job.get("descriptionTeaser") or "",
            f"Categorie : {job.get('category')}" if job.get("category") else "",
            f"Type : {job.get('timeType')}" if job.get("timeType") else "",
            f"Travail : {job.get('remoteType')}" if job.get("remoteType") else "",
            # Phenom fait sa propre extraction de competences: autant s'en servir
            "Competences : " + ", ".join(job["ml_skills"]) if job.get("ml_skills") else "",
        ]
        return "\n".join(p for p in parts if p)


def _places(job: dict[str, Any]) -> str:
    """Villes du poste, dedoublonnees.

    Phenom donne "Wavre, Brabant wallon, Belgique" par lieu; un poste ouvert
    sur cinq sites produirait une ligne de 200 caracteres illisible. On ne
    garde que la ville, qui est ce que l'utilisateur regarde.
    """
    raw = job.get("multi_location") or [job.get("location", "")]
    villes = [place.split(",")[0].strip() for place in raw if place]
    return ", ".join(dict.fromkeys(v for v in villes if v))[:255]


def _as_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None
