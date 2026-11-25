"""Onglet Liste An: une offre masquee par l'utilisateur revient avec
``hidden=True`` (l'interface la range parmi les ecartees), pour lui seul."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ananas.api.liste_an import liste_an_jobs
from ananas.db import Base
from ananas.models import Company, HiddenJob, Job, User


@pytest.fixture
def db():
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def test_offre_masquee_marquee_pour_son_seul_auteur(db):
    alice = User(email="a@example.com", password_hash="x")
    bob = User(email="b@example.com", password_hash="x")
    company = Company(slug="ku-leuven", name="KU Leuven", liste_an_category="Académie")
    db.add_all([alice, bob, company])
    db.commit()
    jobs = [
        Job(company_id=company.id, title=t, url=f"https://example.test/{i}", fingerprint=str(i))
        for i, t in enumerate(["Postdoc A", "PhD B"])
    ]
    db.add_all(jobs)
    db.commit()
    db.add(HiddenJob(user_id=alice.id, job_id=jobs[0].id))
    db.commit()

    seen_by_alice = {j.title: j.hidden for j in liste_an_jobs(db=db, user=alice)}
    seen_by_bob = {j.title: j.hidden for j in liste_an_jobs(db=db, user=bob)}

    assert seen_by_alice == {"Postdoc A": True, "PhD B": False}
    assert seen_by_bob == {"Postdoc A": False, "PhD B": False}
