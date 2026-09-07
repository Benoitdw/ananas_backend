"""Une offre qui gagne ses caracteristiques gagne aussi ses scores.

C'est le lien qui rend l'outil utile: sans ligne dans ``job_matches``, une
offre n'a pas de score dans l'interface, ne peut pas etre triee par pertinence,
et disparait de "seulement les pertinentes". Elle existe sans exister.

**Ces tests ne valent que parce que la session est ouverte comme en
production.** ``SessionLocal`` (voir ``ananas.db``) utilise
``expire_on_commit=False``. Avec le defaut de SQLAlchemy — ``True`` — le bug
que ce fichier verrouille est *invisible*: le commit expire les objets, le
``job.features`` lu a None est recharge, et tout semble marcher. Une fixture
qui oublierait ce parametre rendrait ces tests verts pour de mauvaises raisons.

Le bug: ``_save_job_features`` lisait ``job.features`` (lazy load -> None mis
en cache), creait la ligne avec la seule cle etrangere, committait — et
``score_job_for_all``, appele juste apres sur le meme objet, lisait ce None
cache et abandonnait. Les caracteristiques etaient en base, les scores jamais
calcules. Tous les chemins automatiques passent par la
(``extract_missing_features`` et ``collect_extraction_batches``), et rien ne
rattrapait: seul un reenregistrement de CV recreait des scores.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ananas.ai.service import _save_job_features, rescore_stale, score_job_for_all
from ananas.db import Base
from ananas.models import Company, Job, JobFeatures, JobMatch, User, UserProfile

FEATURES = {
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

PROFILE = {
    "role_families": ["biologie cellulaire"],
    "seniority": "confirme",
    "years_experience": 6,
    "skills": ["culture cellulaire", "western blot"],
    "domains": ["oncologie"],
    "languages": ["fr"],
    "locations": ["Bruxelles, Belgique"],
    "contracts": ["cdi"],
    "remote": "hybride",
    "avoid": [],
    "summary": "",
}


@pytest.fixture
def db():
    """Meme configuration que ``ananas.db.SessionLocal``.

    ``expire_on_commit=False`` n'est pas un detail recopie par acquit de
    conscience: c'est la condition sous laquelle le bug existe.
    """
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    yield session
    session.close()


def make_job(db) -> Job:
    company = Company(slug="acme", name="Acme")
    db.add(company)
    db.commit()
    job = Job(company_id=company.id, fingerprint="f1", title="Chercheur", url="https://x/1")
    db.add(job)
    db.commit()
    return job


def make_profile(db, *, ready: bool = True) -> UserProfile:
    user = User(email="a@example.be", password_hash="x")
    db.add(user)
    db.commit()
    profile = UserProfile(
        user_id=user.id,
        data=PROFILE if ready else None,
        status="ok" if ready else None,
        version=1,
    )
    db.add(profile)
    db.commit()
    return profile


# ------------------------------------------------- caracterisation -> score


def test_offre_caracterisee_est_scoree_dans_la_foulee(db):
    """Le scenario exact du worker: sauver les caracteristiques, puis scorer
    le meme objet ``Job`` en memoire."""
    profile = make_profile(db)
    job = make_job(db)

    _save_job_features(db, job, dict(FEATURES))
    assert score_job_for_all(db, job) == 1

    match = db.get(JobMatch, {"user_id": profile.user_id, "job_id": job.id})
    assert match is not None
    assert match.score > 0


def test_features_rattachees_a_l_offre_en_memoire(db):
    """La cause racine, isolee: apres l'enregistrement, ``job.features`` doit
    etre l'objet ecrit — pas le None lu avant sa creation."""
    job = make_job(db)
    features = _save_job_features(db, job, dict(FEATURES))
    assert job.features is features


def test_recaracterisation_met_a_jour_sans_dupliquer(db):
    job = make_job(db)
    _save_job_features(db, job, dict(FEATURES))
    _save_job_features(db, job, {**FEATURES, "role_family": "biologie moleculaire"})

    assert db.query(JobFeatures).count() == 1
    assert job.features.role_family == "biologie moleculaire"


def test_profil_non_analyse_n_est_pas_score(db):
    """Un profil sans extraction n'a rien a comparer: pas de ligne plutot
    qu'un score calcule sur du vide."""
    make_profile(db, ready=False)
    job = make_job(db)

    _save_job_features(db, job, dict(FEATURES))
    assert score_job_for_all(db, job) == 0
    assert db.query(JobMatch).count() == 0


def test_offre_sans_caracteristiques_n_est_pas_scoree(db):
    make_profile(db)
    assert score_job_for_all(db, make_job(db)) == 0


# ------------------------------------------------------------- rattrapage


def test_rescore_rattrape_une_offre_laissee_sans_score(db):
    """Le filet de ``morning_job``. Simule l'etat laisse en base par le bug:
    des caracteristiques, aucun score."""
    profile = make_profile(db)
    job = make_job(db)
    db.add(JobFeatures(job_id=job.id, **{k: v for k, v in FEATURES.items()}))
    db.commit()
    assert db.query(JobMatch).count() == 0

    assert rescore_stale(db) == 1
    assert db.get(JobMatch, {"user_id": profile.user_id, "job_id": job.id}) is not None


def test_rescore_sans_profil_pret_ne_fait_rien(db):
    make_profile(db, ready=False)
    job = make_job(db)
    _save_job_features(db, job, dict(FEATURES))
    assert rescore_stale(db) == 0
