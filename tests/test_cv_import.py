"""Import d'un CV en PDF.

Un CV mal importe produit un profil faux, donc des scores faux, sans que rien
ne le signale. D'ou deux exigences: le nettoyage du texte doit etre correct, et
tout echec doit produire un message comprehensible plutot qu'un profil vide.
"""

import zlib

import pytest

from ananas.cv_import import MIN_USEFUL_CHARS, CvImportError, _clean, extract_text


def make_pdf(text: str) -> bytes:
    """PDF minimal a une page portant `text` dans un flux de contenu."""
    escaped = text.replace("\\", "").replace("(", "").replace(")", "")
    stream = f"BT /F1 12 Tf 50 750 Td ({escaped}) Tj ET".encode("latin-1", "replace")
    compressed = zlib.compress(stream)

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(compressed)
        + compressed
        + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"

    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref,
    )
    return bytes(out)


# --------------------------------------------------------------- nettoyage


def test_cesure_recollee():
    """'regle-\\nmentaires' doit redonner un mot, sinon le modele lit deux
    fragments qui ne correspondent a aucune competence connue."""
    assert "reglementaires" in _clean("affaires regle-\nmentaires")


def test_retour_ligne_milieu_de_phrase_devient_espace():
    assert _clean("gestion des\ndossiers") == "gestion des dossiers"


def test_paragraphes_conserves():
    assert "\n\n" in _clean("Experience\n\nCompetences")


def test_espaces_normalises():
    assert _clean("trop    d'espaces ici") == "trop d'espaces ici"


# ------------------------------------------------------------- extraction


def test_pdf_lisible():
    texte = "Regulatory Affairs Manager avec sept ans d experience en soumissions eCTD"
    extrait, pages = extract_text(make_pdf(texte))
    assert pages == 1
    assert "Regulatory Affairs Manager" in extrait


def test_fichier_non_pdf_rejete():
    with pytest.raises(CvImportError, match="pas un PDF"):
        extract_text(b"Ceci est un fichier texte")


def test_pdf_tronque_rejete():
    with pytest.raises(CvImportError):
        extract_text(make_pdf("Test")[:300])


def test_fichier_trop_lourd_rejete():
    with pytest.raises(CvImportError, match="trop lourd"):
        extract_text(b"%PDF-1.4" + b"\0" * (11 * 1024 * 1024))


def test_message_destine_a_l_utilisateur():
    """Pas de trace technique: ces messages sont affiches tels quels."""
    with pytest.raises(CvImportError) as exc:
        extract_text(b"pas un pdf")
    message = str(exc.value)
    assert message[0].isupper() and message.endswith(".")


# ------------------------------------------------------ repli sur le modele


def test_pdf_sans_texte_declenche_le_repli(monkeypatch):
    """Un PDF scanne n'a aucune couche texte: sans repli, on enregistrerait un
    profil vide sans que personne s'en apercoive."""
    from ananas import cv_import
    from ananas.ai import registry
    from ananas.ai.base import BaseLLM

    transcription = "Benoit Dewitte " + "affaires reglementaires " * 20

    class FauxModele(BaseLLM):
        key = "faux"
        def complete_json(self, **kwargs): ...
        def is_configured(self): return True
        def read_document(self, **kwargs): return transcription

    monkeypatch.setattr(registry, "get_provider", lambda key=None: FauxModele())
    monkeypatch.setattr(cv_import, "extract_text", lambda data: ("", 1))

    texte, _pages, methode = cv_import.read_cv(b"%PDF-1.4 scan")
    assert methode == "modele"
    assert len(texte) >= MIN_USEFUL_CHARS


def test_sans_repli_message_explicite(monkeypatch):
    """Un fournisseur local sans entree documentaire doit conduire a une
    consigne claire, pas a un profil vide."""
    from ananas import cv_import
    from ananas.ai import registry
    from ananas.ai.base import BaseLLM

    class SansDocument(BaseLLM):
        key = "sans"
        def complete_json(self, **kwargs): ...
        def is_configured(self): return True

    monkeypatch.setattr(registry, "get_provider", lambda key=None: SansDocument())
    monkeypatch.setattr(cv_import, "extract_text", lambda data: ("", 1))

    with pytest.raises(CvImportError, match="copie-colle"):
        cv_import.read_cv(b"%PDF-1.4 scan")
