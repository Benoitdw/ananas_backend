"""Correction manuelle du profil structure.

Ce que le modele a compris est *ce qui sert au calcul des scores*. Le corriger
a la main n'a donc de valeur que si la correction entre dans le meme
vocabulaire que les offres: une competence saisie "Western Blot" doit devenir
le "western blot" que l'extraction produit, sinon elle ne rencontrera jamais
son equivalent cote offre et la correction serait un simple affichage.

Les echelles fermees (niveau, teletravail, contrat) sont refusees plutot que
corrigees en silence: une valeur hors echelle ne peut venir que d'un client qui
ne parle pas le meme vocabulaire, et l'accepter donnerait un profil que le
scoring ignorerait sans rien dire.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ananas.ai.extraction import CONTRACT, REMOTE, SENIORITY, normalize_terms
from ananas.ai.matching import score_job
from ananas.schemas import MAX_PROFILE_TERMS, ProfileDataIn


def data(**kwargs) -> dict:
    return ProfileDataIn(**kwargs).model_dump(exclude_unset=True)


# ------------------------------------------------------- vocabulaire partage


def test_termes_ramenes_au_vocabulaire_de_l_extraction():
    assert data(skills=["  Western Blot ", "ELISA"])["skills"] == ["western blot", "elisa"]


def test_meme_normalisation_que_l_extraction():
    saisi = ["RT-qPCR", "Cytometrie en Flux"]
    assert data(skills=saisi)["skills"] == normalize_terms(saisi)


def test_doublons_a_la_casse_pres_fusionnes():
    assert data(domains=["Oncologie", "oncologie", "ONCOLOGIE"])["domains"] == ["oncologie"]


def test_entrees_vides_ignorees():
    assert data(languages=["fr", "  ", ""])["languages"] == ["fr"]


def test_liste_videe_est_une_valeur_legitime():
    # Retirer le dernier chip d'un champ doit vider ce champ, pas etre ignore
    assert data(avoid=[]) == {"avoid": []}


# ------------------------------------------------------- semantique du PATCH


def test_champ_absent_n_est_pas_touche():
    assert "skills" not in data(languages=["fr"])


def test_liste_trop_longue_refusee():
    with pytest.raises(ValidationError):
        ProfileDataIn(skills=[f"competence {i}" for i in range(MAX_PROFILE_TERMS + 1)])


# --------------------------------------------------------- echelles fermees


def test_niveau_hors_echelle_refuse():
    with pytest.raises(ValidationError):
        ProfileDataIn(seniority="expert")


def test_niveau_accepte_toute_l_echelle_partagee():
    for niveau in SENIORITY:
        assert data(seniority=niveau.upper())["seniority"] == niveau


def test_teletravail_hors_echelle_refuse():
    with pytest.raises(ValidationError):
        ProfileDataIn(remote="teletravail total")


def test_teletravail_accepte_toute_l_echelle_partagee():
    for mode in REMOTE:
        assert data(remote=mode)["remote"] == mode


def test_contrats_bornes_a_l_echelle_partagee():
    assert data(contracts=["CDI", "cdi", CONTRACT[1]])["contracts"] == ["cdi", CONTRACT[1]]
    with pytest.raises(ValidationError):
        ProfileDataIn(contracts=["cdi", "portage salarial"])


def test_annees_d_experience_negatives_refusees():
    with pytest.raises(ValidationError):
        ProfileDataIn(years_experience=-1)


# ---------------------------------------------------- effet reel sur le score


JOB = {
    "role_family": "biologie cellulaire",
    "seniority": "confirme",
    "years_experience_min": 3,
    "contract": "cdi",
    "remote": "hybride",
    "skills": ["culture cellulaire", "western blot"],
    "nice_to_have": [],
    "domains": ["oncologie"],
    "languages": ["fr"],
    "locations": ["Bruxelles, Belgique"],
    "summary": "",
}

PROFIL = {
    "role_families": ["biologie cellulaire"],
    "seniority": "confirme",
    "years_experience": 6,
    "skills": [],
    "domains": ["oncologie"],
    "languages": ["fr"],
    "locations": ["Bruxelles, Belgique"],
    "contracts": ["cdi"],
    "remote": "hybride",
    "avoid": [],
    "summary": "",
}


def test_competence_ajoutee_a_la_main_fait_monter_le_score():
    """Le point du tout: une correction qui ne bougerait pas les scores ne
    serait qu'un affichage."""
    avant = score_job(PROFIL, JOB).score
    apres = score_job({**PROFIL, **data(skills=["Culture Cellulaire", "Western Blot"])}, JOB).score
    assert apres > avant


def test_terme_ajoute_a_eviter_fait_chuter_le_score():
    corrige = {**PROFIL, **data(avoid=["Oncologie"])}
    assert score_job(corrige, JOB).score < score_job(PROFIL, JOB).score
