"""Masquage d'une entreprise: la promesse est "plus jamais rien de cette boite".

Elle porte sur trois surfaces qui n'ont aucun code commun — la carte, le feed
d'offres et la notification quotidienne. Chacune est verifiee ici, parce qu'en
oublier une donnerait exactement le bug que le reglage est cense empecher: un
utilisateur qui croit avoir coupe une entreprise et continue d'en recevoir.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from ananas.db import Base
from ananas.models import (
    Company,
    HiddenCompany,
    Job,
    SavedCompany,
    User,
)
from ananas.worker.notify import pending_jobs, unscraped_saved_companies


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def user(db) -> User:
    user = User(email="a@example.com", password_hash="x")
    db.add(user)
    db.commit()
    return user


def make_company(db, name: str, with_scraper: bool = True) -> Company:
    # `scraper_key` est unique en base: on le derive du nom.
    company = Company(
        slug=name.lower(), name=name, scraper_key=name.lower() if with_scraper else None
    )
    db.add(company)
    db.commit()
    return company


def make_job(db, company: Company, title: str = "Chercheur") -> Job:
    job = Job(
        company_id=company.id,
        title=title,
        url=f"https://example.test/{title}",
        fingerprint=f"{company.id}-{title}",
    )
    db.add(job)
    db.commit()
    return job


def hide(db, user: User, company: Company) -> None:
    db.add(HiddenCompany(user_id=user.id, company_id=company.id))
    db.commit()


def save(db, user: User, company: Company) -> None:
    db.add(SavedCompany(user_id=user.id, company_id=company.id))
    db.commit()


def test_offre_d_une_entreprise_masquee_n_est_jamais_notifiee(db, user):
    """Le coeur de la promesse: le digest quotidien ne la voit plus."""
    company = make_company(db, "Acme")
    save(db, user, company)
    make_job(db, company)
    assert len(pending_jobs(db, user.id)) == 1

    hide(db, user, company)
    assert pending_jobs(db, user.id) == []


def test_masquage_tient_meme_si_le_favori_a_survecu(db, user):
    """`hide_company` retire le favori, mais la notification ne s'y fie pas.

    On force ici l'etat incoherent que l'API interdit — favori *et* masquee —
    pour verifier que c'est bien le masquage qui l'emporte, et non l'invariant
    maintenu ailleurs.
    """
    company = make_company(db, "Acme")
    save(db, user, company)
    hide(db, user, company)
    make_job(db, company)

    assert pending_jobs(db, user.id) == []


def test_une_autre_entreprise_continue_d_etre_notifiee(db, user):
    """Masquer coupe une boite, pas la veille entiere."""
    masquee, suivie = make_company(db, "Acme"), make_company(db, "Globex")
    save(db, user, masquee)
    save(db, user, suivie)
    make_job(db, masquee)
    make_job(db, suivie, title="Analyste")
    hide(db, user, masquee)

    rows = pending_jobs(db, user.id)
    assert [company.name for _, company, _ in rows] == ["Globex"]


def test_masquage_est_personnel(db, user):
    """Le reglage d'un utilisateur ne retire l'entreprise a personne d'autre."""
    autre = User(email="b@example.com", password_hash="x")
    db.add(autre)
    db.commit()

    company = make_company(db, "Acme")
    save(db, user, company)
    save(db, autre, company)
    make_job(db, company)
    hide(db, user, company)

    assert pending_jobs(db, user.id) == []
    assert len(pending_jobs(db, autre.id)) == 1


def test_pied_de_page_ne_nomme_pas_une_entreprise_masquee(db, user):
    """Signaler "pas de veille automatique" sur une boite qu'on a coupee
    reviendrait a en reparler tous les jours."""
    company = make_company(db, "Acme", with_scraper=False)
    save(db, user, company)
    assert unscraped_saved_companies(db, user.id) == ["Acme"]

    hide(db, user, company)
    assert unscraped_saved_companies(db, user.id) == []


def test_masquer_puis_demasquer_rend_les_offres(db, user):
    """Le reglage est reversible sans perte: les offres jamais notifiees le
    restent, elles repassent au run suivant."""
    company = make_company(db, "Acme")
    save(db, user, company)
    make_job(db, company)
    hide(db, user, company)
    assert pending_jobs(db, user.id) == []

    db.delete(db.get(HiddenCompany, {"user_id": user.id, "company_id": company.id}))
    db.commit()
    assert len(pending_jobs(db, user.id)) == 1


def test_pk_composite_rend_le_masquage_idempotent(db, user):
    """Deux masquages du meme couple ne peuvent pas coexister en base."""
    company = make_company(db, "Acme")
    hide(db, user, company)

    rows = db.scalars(
        select(HiddenCompany).where(
            HiddenCompany.user_id == user.id, HiddenCompany.company_id == company.id
        )
    ).all()
    assert len(rows) == 1
