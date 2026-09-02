"""Correspondance profil/offre.

Le calcul est deterministe et n'appelle aucun modele: c'est precisement ce qui
le rend testable. Ces tests fixent le comportement attendu du score, qui pilote
a la fois le tri des notifications et le filtre "offres pertinentes".
"""

import pytest

from ananas.ai.matching import score_job, similar

BASE_PROFILE = {
    "role_families": ["affaires reglementaires"],
    "seniority": "senior",
    "years_experience": 7,
    "skills": ["ectd", "ctd", "soumission reglementaire", "gestion de projet"],
    "domains": ["industrie pharmaceutique"],
    "languages": ["fr", "en"],
    "locations": ["bruxelles, belgique"],
    "remote": "hybride",
    "avoid": [],
}

BASE_JOB = {
    "role_family": "affaires reglementaires",
    "seniority": "senior",
    "years_experience_min": 6,
    "contract": "cdi",
    "remote": "hybride",
    "skills": ["ectd", "ctd", "soumission reglementaire"],
    "nice_to_have": [],
    "domains": ["industrie pharmaceutique"],
    "languages": ["en"],
    "locations": ["bruxelles, belgique"],
    "summary": "",
}


def profile(**over):
    return {**BASE_PROFILE, **over}


def job(**over):
    return {**BASE_JOB, **over}


# ------------------------------------------------------ rapprochement lexical


@pytest.mark.parametrize(
    "a, b",
    [
        ("gestion de projet", "gestion projet"),
        ("affaires reglementaires", "affaires reglementaires"),
        ("assurance qualite", "assurance qualite pharmaceutique"),
    ],
)
def test_termes_equivalents(a, b):
    assert similar(a, b)


@pytest.mark.parametrize("a, b", [("python", "java"), ("audit", "achat"), ("ectd", "")])
def test_termes_distincts(a, b):
    assert not similar(a, b)


# ----------------------------------------------------------------- le score


def test_correspondance_parfaite_est_haute():
    assert score_job(profile(), job()).score >= 85


def test_metier_different_fait_chuter():
    """C'est le signal le plus discriminant: meme secteur, autre metier."""
    ailleurs = job(role_family="developpement commercial", skills=["negociation", "prospection"])
    assert score_job(profile(), ailleurs).score < score_job(profile(), job()).score - 30


def test_score_borne():
    for candidat in (job(), job(skills=[], domains=[], languages=[], locations=[])):
        assert 0 <= score_job(profile(), candidat).score <= 100


def test_rejet_explicite_ecrase_le_score():
    """Une offre par ailleurs parfaite doit tomber si elle porte ce que la
    personne a dit vouloir eviter."""
    sans = score_job(profile(), job()).score
    avec = score_job(profile(avoid=["ectd"]), job()).score
    assert avec < sans - 30


def test_rejet_apparait_dans_les_raisons():
    result = score_job(profile(avoid=["ectd"]), job())
    assert any("eviter" in r for r in result.reasons)


# ------------------------------------------------------------- seniorite


def test_poste_un_cran_au_dessus_reste_atteignable():
    au_dessus = score_job(profile(seniority="confirme", years_experience=6), job()).score
    beaucoup = score_job(profile(seniority="junior", years_experience=6), job()).score
    assert au_dessus > beaucoup


def test_annees_manquantes_penalisent():
    experimente = score_job(profile(years_experience=10), job()).score
    debutant = score_job(profile(years_experience=1), job()).score
    assert debutant < experimente


def test_annees_manquantes_expliquees():
    result = score_job(profile(years_experience=1), job(years_experience_min=8))
    assert any("8 ans demandes" in r for r in result.reasons)


# ------------------------------------------------------- competences, langues


def test_recouvrement_partiel_donne_score_intermediaire():
    partiel = score_job(profile(skills=["ectd"]), job()).score
    complet = score_job(profile(), job()).score
    aucun = score_job(profile(skills=["python"]), job()).score
    assert aucun < partiel < complet


def test_langue_exigee_absente_penalise():
    avec = score_job(profile(languages=["fr", "en", "nl"]), job(languages=["nl"])).score
    sans = score_job(profile(languages=["fr"]), job(languages=["nl"])).score
    assert sans < avec


def test_offre_sans_exigence_ne_penalise_pas_a_l_aveugle():
    """Beaucoup d'annonces ne listent aucune competence: leur donner 0 les
    ferait toutes disparaitre du filtre de pertinence."""
    muette = score_job(profile(), job(skills=[])).score
    hors_sujet = score_job(profile(), job(skills=["soudure", "plomberie"])).score
    assert muette > hors_sujet


# ------------------------------------------------------------- explicabilite


def test_les_raisons_sont_lisibles():
    result = score_job(profile(), job())
    assert result.reasons
    assert all(isinstance(r, str) and r.strip() for r in result.reasons)


def test_detail_par_critere_disponible():
    """Le detail sert a comprendre un score surprenant."""
    result = score_job(profile(), job())
    assert set(result.parts) == {
        "skills", "role", "seniority", "domains", "languages", "location", "remote"
    }
