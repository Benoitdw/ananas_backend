"""Lecture d'un CV en PDF.

Deux chemins, dans cet ordre:

1. **Extraction de texte locale** (pypdf). Gratuite, instantanee, independante
   du fournisseur de modele — c'est le cas de la grande majorite des CV, qui
   sont exportes depuis un traitement de texte.
2. **Repli sur le modele** pour les PDF *scannes*, ou il n'y a aucun texte a
   extraire, seulement une image. Ce repli est optionnel: un fournisseur qui
   ne sait pas lire un document leve NotImplementedError et on le dit
   clairement a l'utilisateur, plutot que d'enregistrer un profil vide.

Le texte obtenu n'est jamais analyse directement: il remplit le champ CV, que
l'utilisateur relit et corrige avant de lancer l'analyse. Une extraction PDF
melange souvent les colonnes.
"""

from __future__ import annotations

import io
import logging
import re

from pypdf import PdfReader
from pypdf.errors import PdfReadError

log = logging.getLogger(__name__)

MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 20
# En dessous, on considere qu'il n'y a pas de texte exploitable: PDF scanne,
# ou CV entierement compose d'images.
MIN_USEFUL_CHARS = 200


class CvImportError(RuntimeError):
    """Message destine a l'utilisateur, pas une trace technique."""


def _clean(raw: str) -> str:
    """Rend le texte d'un PDF lisible.

    Les extractions produisent des cesures en fin de ligne et des retours
    arbitraires au milieu des phrases: on les recolle, sinon le modele lit des
    mots coupes.
    """
    text = raw.replace("\r\n", "\n").replace("\xa0", " ")
    # "regle-\nmentaires" -> "reglementaires"
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    # Retour simple au milieu d'une phrase -> espace; on garde les paragraphes
    text = re.sub(r"(?<![\n.:;•\-])\n(?![\n•\-•])", " ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text(data: bytes) -> tuple[str, int]:
    """Texte et nombre de pages. Leve CvImportError si le PDF est illisible."""
    if len(data) > MAX_BYTES:
        # La lecture est plafonnee en amont: on ne connait pas la taille reelle,
        # inutile de l'annoncer.
        raise CvImportError(f"Fichier trop lourd : {MAX_BYTES // 1024 // 1024} Mo au maximum.")
    if not data.startswith(b"%PDF"):
        raise CvImportError("Ce fichier n'est pas un PDF.")

    try:
        reader = PdfReader(io.BytesIO(data))
    except PdfReadError as exc:
        raise CvImportError(f"PDF illisible : {exc}") from exc

    if reader.is_encrypted:
        # Un PDF protege par mot de passe: pypdf tente le mot de passe vide,
        # ce qui suffit pour les PDF simplement "proteges en modification".
        try:
            reader.decrypt("")
        except Exception as exc:  # noqa: BLE001
            raise CvImportError("Ce PDF est protege par un mot de passe.") from exc

    pages = reader.pages[:MAX_PAGES]
    try:
        chunks = [page.extract_text() or "" for page in pages]
    except Exception as exc:  # noqa: BLE001
        raise CvImportError(f"Extraction impossible : {exc}") from exc

    return _clean("\n\n".join(chunks)), len(reader.pages)


def read_cv(data: bytes) -> tuple[str, int, str]:
    """(texte, pages, methode). ``methode`` vaut 'texte' ou 'modele'."""
    text, pages = extract_text(data)
    if len(text) >= MIN_USEFUL_CHARS:
        return text, pages, "texte"

    # Pas de couche texte: probablement un scan. On tente le modele s'il sait
    # lire un document.
    from ananas.ai.base import LLMError
    from ananas.ai.registry import get_provider

    provider = get_provider()
    if provider is not None and provider.is_configured():
        try:
            transcribed = provider.read_document(
                data=data,
                mime_type="application/pdf",
                instruction=(
                    "Transcris integralement le texte de ce CV, dans l'ordre de lecture. "
                    "Conserve les intitules de poste, les dates, les competences et les "
                    "langues. N'ajoute aucun commentaire."
                ),
            ).strip()
            if len(transcribed) >= MIN_USEFUL_CHARS:
                return _clean(transcribed), pages, "modele"
        except NotImplementedError:
            log.info("Le fournisseur actif ne sait pas lire un document.")
        except LLMError as exc:
            log.warning("Transcription du PDF impossible: %s", exc)

    raise CvImportError(
        "Aucun texte n'a pu etre extrait. Ce PDF est probablement un scan ou une "
        "image : copie-colle le texte de ton CV dans le champ ci-dessous."
    )
