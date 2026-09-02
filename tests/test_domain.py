"""Detection de doublons par domaine.

Deux personnes ecrivent rarement le nom d'une entreprise de la meme facon,
mais pointent le meme site. Sans cette comparaison, le repertoire partage se
remplit de doublons.
"""

import pytest

from ananas.api.companies import _domain


@pytest.mark.parametrize(
    "a, b",
    [
        ("https://www.imcyse.com/", "https://imcyse.com"),
        ("http://IMCYSE.com", "https://www.imcyse.com/fr/careers"),
        ("imcyse.com", "https://www.imcyse.com"),
    ],
)
def test_memes_domaines(a, b):
    assert _domain(a) == _domain(b) != ""


@pytest.mark.parametrize("a, b", [("https://acme.com", "https://acme.be"), ("acme.com", "")])
def test_domaines_differents(a, b):
    assert _domain(a) != _domain(b)


def test_url_vide():
    assert _domain("") == ""
