"""Qui peut modifier une fiche du repertoire.

Le repertoire est partage: une fiche mal corrigee est visible de tous, et une
fiche BioWin ou Ananas n'appartient a aucun compte. La regle doit donc etre
etroite — l'administration partout, l'utilisateur sur sa seule proposition —
et le fait qu'elle vive dans une fonction unique est ce qui empeche l'API et
l'interface d'en avoir deux versions divergentes.
"""

import pytest

from ananas.api.companies import _bare_city, may_edit
from ananas.models import SOURCE_BIOWIN, SOURCE_CURATED, SOURCE_USER, Company, User


def company(**kwargs) -> Company:
    kwargs.setdefault("source", SOURCE_BIOWIN)
    return Company(name="Acme", slug="acme", **kwargs)


def user(user_id: int, admin: bool = False) -> User:
    return User(id=user_id, email=f"u{user_id}@x.be", password_hash="x", is_admin=admin)


def test_visiteur_anonyme_ne_modifie_rien():
    assert may_edit(company(), None) is False


def test_utilisateur_ne_touche_pas_au_repertoire_partage():
    for source in (SOURCE_BIOWIN, SOURCE_CURATED):
        assert may_edit(company(source=source), user(7)) is False


def test_utilisateur_modifie_sa_propre_proposition():
    proposee = company(source=SOURCE_USER, submitted_by_user_id=7)
    assert may_edit(proposee, user(7)) is True


def test_utilisateur_ne_modifie_pas_la_proposition_d_un_autre():
    proposee = company(source=SOURCE_USER, submitted_by_user_id=8)
    assert may_edit(proposee, user(7)) is False


def test_administrateur_modifie_tout():
    admin = user(1, admin=True)
    assert may_edit(company(), admin) is True
    assert may_edit(company(source=SOURCE_USER, submitted_by_user_id=8), admin) is True


@pytest.mark.parametrize(
    "stocke, attendu",
    [
        ("1210 BRUXELLES", "BRUXELLES"),
        ("3012 Leuven", "Leuven"),
        ("Leuven", "Leuven"),
        ("", ""),
        # Un code postal seul reste tel quel: il n'y a rien a garder derriere
        ("1210", "1210"),
    ],
)
def test_ville_sans_code_postal(stocke, attendu):
    """Le formulaire d'edition reaffiche `city` telle qu'elle est stockee,
    code postal compris. Sans ce nettoyage, deux enregistrements successifs
    donneraient '1210 1210 BRUXELLES'."""
    assert _bare_city(stocke) == attendu
