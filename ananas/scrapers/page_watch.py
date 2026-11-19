"""Base pour les pages carrieres sans offre structuree: on surveille l'etat vide.

Beaucoup de petites biotechs ont une page carrieres qui, la plupart du temps,
affiche seulement « aucune offre pour le moment ». Impossible d'ecrire un
parseur d'offres sans jamais en avoir vu une: le jour ou un poste apparait, un
selecteur devine aurait toutes les chances de rater.

On surveille donc ce que l'on *connait*: la phrase d'etat vide.

- Tant qu'une des ``empty_markers`` figure dans la zone surveillee: 0 offre.
- Si elle disparait, la page a change. On renvoie **une** offre qui pointe vers
  la page carrieres, avec le texte de la zone en description (l'extraction de
  caracteristiques et le score travaillent dessus comme sur une vraie annonce).
  Son identifiant est un hash du texte: un nouveau changement donne une
  nouvelle offre, et donc une nouvelle notification.
- Si la zone elle-meme a disparu (refonte du site), on leve une exception: le
  scraper passe en erreur plutot que de rendre 0 offre en silence.

C'est le moment d'ecrire un vrai parseur pour cette entreprise.
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import ClassVar

from ananas.scrapers.base import BaseScraper, JobPosting
from ananas.scrapers.http import txt

log = logging.getLogger(__name__)


class PageWatchScraper(BaseScraper):
    """Sous-classer et definir ``key``, ``careers_url``, ``empty_markers``.

    Ne pas enregistrer cette classe: elle n'a pas de ``key``.
    """

    # Zone de la page a surveiller (selecteur CSS). Vide = tout le <body>.
    region: ClassVar[str] = ""
    # Phrases (insensibles a la casse) qui signifient « aucune offre ».
    empty_markers: ClassVar[tuple[str, ...]] = ()

    def fetch(self) -> list[JobPosting]:
        soup = self.get_soup(self.careers_url)
        for node in soup(["script", "style", "noscript", "svg"]):
            node.decompose()
        zone = soup.select_one(self.region) if self.region else soup.body
        if zone is None:
            raise RuntimeError(
                f"zone '{self.region}' introuvable sur {self.careers_url}: "
                "la page a ete refondue, le scraper est a revoir"
            )

        if self.is_empty(zone):
            return []
        text = txt(zone)
        folded = _fold(text)

        log.warning(
            "%s: l'etat « aucune offre » a disparu de %s — offre(s) probable(s), "
            "parseur dedie a ecrire",
            self.key,
            self.careers_url,
        )
        digest = hashlib.sha256(folded.encode("utf-8")).hexdigest()[:16]
        name = self.label or self.key
        return [
            JobPosting(
                title=f"{name} : nouvelle(s) offre(s) sur la page carrieres",
                url=self.careers_url,
                description=text[:8000],
                external_id=f"page-watch:{digest}",
            )
        ]

    def is_empty(self, zone) -> bool:
        """Vrai si la zone affiche l'etat « aucune offre ». A surcharger quand
        l'etat vide n'est pas une phrase (onglet vide...)."""
        folded = _fold(txt(zone))
        return any(_fold(marker) in folded for marker in self.empty_markers)


def _fold(value: str) -> str:
    """Espaces normalises et casse ignoree, apostrophes typographiques unifiees."""
    return re.sub(r"\s+", " ", value.replace("’", "'")).strip().casefold()
