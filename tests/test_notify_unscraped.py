"""Pied de page "pas de veille automatique" du digest quotidien.

Sans lui, un utilisateur qui suit une entreprise sans scraper croirait que le
silence de la notification veut dire "rien de nouveau" — alors que personne
n'est jamais alle regarder.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ananas.db import Base
from ananas.models import Company, SavedCompany, User
from ananas.notifiers.base import Digest, JobLine
from ananas.notifiers.telegram import TelegramNotifier
from ananas.worker import notify
from ananas.worker.notify import build_digest, unscraped_saved_companies


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def save(db, user, company):
    db.add(SavedCompany(user_id=user.id, company_id=company.id))
    db.commit()


def make_user(db) -> User:
    user = User(email="a@example.com", password_hash="x")
    db.add(user)
    db.commit()
    return user


# ------------------------------------------------------- unscraped_saved_companies


def test_sans_scraper_key_est_signalee(db):
    # scraper_key vide court-circuite avant meme d'interroger le registre:
    # pas besoin de le simuler ici.
    user = make_user(db)
    company = Company(slug="acme", name="Acme", scraper_key=None)
    db.add(company)
    db.commit()
    save(db, user, company)

    assert unscraped_saved_companies(db, user.id) == ["Acme"]


def test_scraper_key_orpheline_est_signalee(db, monkeypatch):
    """scraper_key renseignee mais absente du registre: module retire ou en
    erreur au chargement — meme situation cote utilisateur que pas de scraper
    du tout.

    On monkeypatch ``get_scraper`` tel qu'importe dans ``notify.py``, jamais
    le registre partage (``ananas.scrapers.registry.SCRAPERS``): c'est un
    singleton peuple une seule fois par ``load_scrapers()``, et le vider
    ferait perdre pour de bon les scrapers dont aucun autre test ne
    reimporte le module (l'import ne se rejoue pas, Python le sert depuis
    son cache) — une pollution qui survivrait a ce test.
    """
    monkeypatch.setattr(notify, "get_scraper", lambda key: None)
    user = make_user(db)
    company = Company(slug="acme", name="Acme", scraper_key="acme-disparu")
    db.add(company)
    db.commit()
    save(db, user, company)

    assert unscraped_saved_companies(db, user.id) == ["Acme"]


def test_scraper_fonctionnel_n_est_pas_signale(db, monkeypatch):
    monkeypatch.setattr(notify, "get_scraper", lambda key: object if key == "qbd-group" else None)
    user = make_user(db)
    company = Company(slug="qbd-group", name="QbD Group", scraper_key="qbd-group")
    db.add(company)
    db.commit()
    save(db, user, company)

    assert unscraped_saved_companies(db, user.id) == []


def test_entreprises_non_suivies_ignorees(db):
    user = make_user(db)
    db.add(Company(slug="acme", name="Acme", scraper_key=None))
    db.commit()
    # jamais enregistree par l'utilisateur

    assert unscraped_saved_companies(db, user.id) == []


# ------------------------------------------------------------------- build_digest


def test_build_digest_vehicule_les_entreprises_sans_scraper():
    digest = build_digest([], unscraped=["Acme", "Zenith"])
    assert digest.unscraped_companies == ["Acme", "Zenith"]


def test_build_digest_par_defaut_liste_vide():
    digest = build_digest([])
    assert digest.unscraped_companies == []


# --------------------------------------------------------- rendu Telegram


def sample_digest(unscraped: list[str]) -> Digest:
    return Digest(
        companies={"Acme": [JobLine(title="Data Engineer", url="https://acme.example/1")]},
        unscraped_companies=unscraped,
    )


def test_rendu_mentionne_les_entreprises_sans_scraper():
    html = TelegramNotifier().render(sample_digest(["Zenith Biotech"]))
    assert "Zenith Biotech" in html
    assert "veille automatique" in html


def test_rendu_sans_entreprise_sans_scraper_reste_silencieux():
    html = TelegramNotifier().render(sample_digest([]))
    assert "veille automatique" not in html
