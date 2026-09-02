"""Les tags n'ont de valeur que s'ils sont reutilises.

Un tag saisi par un utilisateur sert aux *autres* a filtrer. Si trois
orthographes de "biotech" coexistent, le filtre se remplit de quasi-doublons
et ne sert plus a rien. Ces tests verrouillent la normalisation.
"""

import pytest
from pydantic import ValidationError

from ananas.schemas import MAX_TAGS, CompanySubmitIn, normalize_tag


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("BIOTECH ", "Biotech"),
        (" biotech", "Biotech"),
        ("Biotech", "Biotech"),
        ("medical  devices", "Medical Devices"),
        ("  ,; ", ""),
        ("", ""),
    ],
)
def test_normalisation(raw, expected):
    assert normalize_tag(raw) == expected


@pytest.mark.parametrize("sigle", ["IVD", "CRO", "IA", "R&D"])
def test_sigles_preserves(sigle):
    """Capitaliser 'IVD' en 'Ivd' rendrait le tag meconnaissable."""
    assert normalize_tag(sigle) == sigle


def test_tag_tronque():
    assert len(normalize_tag("a" * 200)) == 60


def submit(**kwargs) -> CompanySubmitIn:
    return CompanySubmitIn(name="Acme", **kwargs)


def test_variantes_dedoublonnees():
    assert submit(tags=["BIOTECH", "biotech", " Biotech "]).tags == ["Biotech"]


def test_ordre_de_saisie_conserve():
    assert submit(tags=["Medtech", "Biotech", "IVD"]).tags == ["Medtech", "Biotech", "IVD"]


def test_tags_vides_ignores():
    assert submit(tags=["Biotech", "", "  ", ",;"]).tags == ["Biotech"]


def test_trop_de_tags_refuse():
    with pytest.raises(ValidationError):
        submit(tags=[f"tag{i}" for i in range(MAX_TAGS + 1)])


def test_url_sans_schema_completee():
    """Un utilisateur tape 'acme.com'; un href relatif casserait le lien."""
    assert submit(website="acme.com").website == "https://acme.com"
    assert submit(website="http://acme.com").website == "http://acme.com"
    assert submit(website="").website == ""


def test_nom_trop_court_refuse():
    with pytest.raises(ValidationError):
        CompanySubmitIn(name="A")


def test_enregistrement_actif_par_defaut():
    """On propose surtout une entreprise qu'on veut soi-meme suivre."""
    assert submit().save is True
