"""Distances au domicile: la mesure, et ce qu'on fait quand elle manque.

Le point delicat n'est pas la trigonometrie — c'est le cas ou la distance est
inconnue. Une entreprise sans coordonnees ne doit ni valoir 0 km (elle
remonterait en tete du tri "le plus proche"), ni disparaitre des listes: cinq
des partenaires importes n'ont aucune adresse publiee.
"""

import pytest

from ananas.distance import distance_from, haversine_km

BRUXELLES = (50.8503, 4.3517)
LIEGE = (50.6326, 5.5797)
GAND = (51.0543, 3.7174)


def test_distance_connue_entre_deux_villes():
    # ~88 km a vol d'oiseau; on tolere l'ecart du modele spherique
    assert haversine_km(*BRUXELLES, *LIEGE) == pytest.approx(89, abs=3)


def test_distance_nulle_sur_le_meme_point():
    assert haversine_km(*BRUXELLES, *BRUXELLES) == 0


def test_distance_symetrique():
    assert haversine_km(*BRUXELLES, *GAND) == pytest.approx(haversine_km(*GAND, *BRUXELLES))


def test_distance_arrondie_au_dixieme_de_km():
    valeur = distance_from(BRUXELLES, *GAND)
    assert valeur is not None
    assert valeur == round(valeur, 1)


def test_sans_domicile_aucune_distance():
    assert distance_from(None, *GAND) is None


def test_sans_coordonnees_d_entreprise_aucune_distance():
    # Pas 0: sans quoi une entreprise non localisee passerait pour la plus proche
    assert distance_from(BRUXELLES, None, None) is None
    assert distance_from(BRUXELLES, 51.0, None) is None


def test_tri_par_distance_relegue_les_inconnues_en_fin():
    """Le comparateur utilise par l'API (companies.list_companies)."""
    items = [
        ("sans position", None),
        ("Liege", distance_from(BRUXELLES, *LIEGE)),
        ("Gand", distance_from(BRUXELLES, *GAND)),
    ]
    ordonne = sorted(items, key=lambda i: (i[1] is None, i[1] or 0.0, i[0]))
    assert [nom for nom, _ in ordonne] == ["Gand", "Liege", "sans position"]
