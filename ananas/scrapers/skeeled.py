"""Base pour les entreprises qui publient leurs offres via Skeeled.

Skeeled (ATS luxembourgeois) n'a pas de page de liste publique: c'est le site
du client qui liste ses offres et pointe chaque annonce vers
``https://app.skeeled.com/offer/c/<id>``. On lit donc la page carrieres du
client pour trouver ces liens, puis chaque fiche Skeeled.

La fiche est rendue cote serveur (Nuxt): le titre est dans ``<title>`` /
``og:description`` et le texte de l'annonce dans le ``<body>``. ``<id>`` est
l'identifiant du canal de publication Skeeled, stable pour une offre.

Les candidatures spontanees passent par le meme type de lien: leurs
identifiants sont a lister dans ``ignore_ids``.
"""

from __future__ import annotations

import logging
import re
from typing import ClassVar

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import txt

log = logging.getLogger(__name__)

_OFFER = re.compile(r"app\.skeeled\.com/offer/c/([0-9a-f]{24})")
# Texte d'interface Skeeled qui precede l'annonce sur la fiche
_PREAMBLE = re.compile(
    r"^.*?Vous êtes en train de commencer votre processus de candidature pour:.*?Postuler maintenant",
    re.DOTALL,
)


class SkeeledScraper(BaseScraper):
    """Sous-classer et definir ``key`` et ``careers_url`` (page du client).

    Ne pas enregistrer cette classe: elle n'a pas de ``key``.
    """

    # Identifiants Skeeled a ignorer (candidature spontanee permanente...)
    ignore_ids: ClassVar[frozenset[str]] = frozenset()
    default_location: ClassVar[str] = ""
    rate_limit: ClassVar[float] = 0.4

    def fetch(self) -> list[JobPosting]:
        soup = self.get_soup(self.careers_url)
        offers: dict[str, str] = {}
        for a in soup.select("a[href*='app.skeeled.com/offer/']"):
            match = _OFFER.search(a["href"])
            if match and match.group(1) not in self.ignore_ids:
                offers.setdefault(match.group(1), txt(a))
        postings = [self._detail(offer_id, label) for offer_id, label in offers.items()]
        log.info("%s: %d offres", self.key, len(postings))
        return postings

    def _detail(self, offer_id: str, label: str) -> JobPosting:
        url = f"https://app.skeeled.com/offer/c/{offer_id}"
        title, description = label, ""
        try:
            soup = self.get_soup(f"{url}?show_description=true")
            meta = soup.select_one("meta[property='og:description'], meta[name='description']")
            title = (meta.get("content") if meta else "") or title
            for node in soup(["script", "style", "noscript"]):
                node.decompose()
            description = _PREAMBLE.sub("", txt(soup.body)).strip()[:8000]
        except Exception as exc:  # noqa: BLE001
            # Une fiche illisible ne fait pas perdre l'offre: on garde le
            # libelle du lien de la page client.
            log.warning("%s: fiche %s illisible (%s)", self.key, url, exc)
        return JobPosting(
            title=title.strip(),
            url=url,
            location=self.default_location or None,
            description=description,
            external_id=offer_id,
        )
