"""Classe parente de tous les scrapers d'offres d'emploi.

Ecrire un scraper = creer un fichier dans ce package, decorer une sous-classe
de ``BaseScraper`` avec ``@register`` et implementer la SEULE methode
``fetch()``. Tout le reste (chronometrage, capture des erreurs, deduplication,
rejet des offres incompletes, journalisation) est fourni par ``run()``.

Exemple minimal::

    @register
    class AcmeScraper(BaseScraper):
        key = "acme"
        careers_url = "https://acme.com/jobs"

        def fetch(self) -> list[JobPosting]:
            soup = self.get_soup(self.careers_url)
            return [
                JobPosting(
                    title=txt(a),
                    url=self.absolutize(a["href"]),
                )
                for a in soup.select("a.job-link")
            ]
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING, ClassVar
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

from ananas.scrapers import http

if TYPE_CHECKING:
    from ananas.models import Company

log = logging.getLogger(__name__)


def _normalize_url(url: str) -> str:
    """Enleve la query, le fragment et le slash final.

    Beaucoup de sites ajoutent des parametres de tracking (?utm_source=...)
    qui changent a chaque visite: sans ce nettoyage, la meme offre serait vue
    comme nouvelle tous les jours.
    """
    parts = urlsplit(url.strip())
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))


def _normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title).strip().lower()


@dataclass(frozen=True)
class JobPosting:
    """Une offre telle que renvoyee par un scraper. Objet de transport pur:
    il ne touche pas a la base."""

    title: str
    url: str
    location: str | None = None
    description: str | None = None
    posted_at: date | None = None
    # Identifiant fourni par le site lui-meme, s'il en expose un (ref, id API).
    # A privilegier: il survit a un changement d'URL ou de libelle.
    external_id: str | None = None
    raw: dict = field(default_factory=dict, compare=False, repr=False)

    @property
    def fingerprint(self) -> str:
        """Identite stable d'une offre, sur 64 caracteres hex.

        C'est la cle de toute la detection de nouveaute: deux passages du
        worker doivent produire le meme fingerprint pour une offre inchangee.
        """
        if self.external_id:
            seed = f"id:{self.external_id.strip()}"
        else:
            seed = f"{_normalize_url(self.url)}|{_normalize_title(self.title)}"
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()

    def is_valid(self) -> bool:
        return bool(self.title and self.title.strip() and self.url and self.url.startswith("http"))


class ScraperError(RuntimeError):
    """Echec de scraping d'une entreprise. Isole: n'interrompt pas le run."""


class BaseScraper(ABC):
    # Identifiant unique du scraper. Doit correspondre a companies.scraper_key.
    key: ClassVar[str]
    # URL de la page carrieres. Sert de defaut si la colonne careers_url est vide.
    careers_url: ClassVar[str] = ""
    # Pause entre deux requetes a l'interieur d'un meme scraper (politesse)
    rate_limit: ClassVar[float] = 0.3
    # Libelle lisible, pour les logs
    label: ClassVar[str] = ""

    def __init__(self, company: Company | None = None, session: requests.Session | None = None):
        self.company = company
        self.session = session or http.session
        # La valeur en base prime sur la constante de classe: tu peux corriger
        # une URL cassee sans redeployer.
        if company is not None and company.careers_url:
            self.careers_url = company.careers_url

    # ------------------------------------------------------------ a implementer

    @abstractmethod
    def fetch(self) -> list[JobPosting]:
        """Retourne les offres actuellement publiees. Seul point a ecrire.

        Lever une exception est acceptable: ``run()`` la capture et la
        transforme en ScraperError, l'entreprise sera marquee en erreur et le
        reste du run continuera.
        """

    # ------------------------------------------------------------- utilitaires

    def get_soup(self, url: str) -> BeautifulSoup:
        soup = http.get_soup(url, sess=self.session)
        self.sleep()
        return soup

    def get_json(self, url: str, **kwargs):
        data = http.get_json(url, sess=self.session, **kwargs)
        self.sleep()
        return data

    def absolutize(self, href: str) -> str:
        return urljoin(self.careers_url, href)

    def sleep(self) -> None:
        if self.rate_limit:
            time.sleep(self.rate_limit)

    # -------------------------------------------------------- template method

    def run(self) -> list[JobPosting]:
        """Execute fetch() et nettoie son resultat. Ne pas surcharger."""
        name = self.company.name if self.company else self.key
        started = time.monotonic()
        try:
            raw = self.fetch()
        except Exception as exc:  # noqa: BLE001 — on veut vraiment tout capturer
            raise ScraperError(f"{self.key}: {type(exc).__name__}: {exc}") from exc

        seen: set[str] = set()
        postings: list[JobPosting] = []
        dropped = 0
        for posting in raw:
            if not posting.is_valid():
                dropped += 1
                continue
            fp = posting.fingerprint
            if fp in seen:
                continue
            seen.add(fp)
            postings.append(posting)

        elapsed = time.monotonic() - started
        detail = f" ({dropped} incompletes ignorees)" if dropped else ""
        log.info("%s: %d offres en %.1fs%s", name, len(postings), elapsed, detail)
        return postings
