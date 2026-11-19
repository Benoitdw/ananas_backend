"""Import d'une liste (``data/liste-an.csv``): une ligne designe une fiche.

La promesse: une entreprise deja au repertoire (BioWin, BioPark, proposee par
un utilisateur) n'est ni dupliquee ni modifiee par la liste — elle recoit
seulement le tag de la liste. C'est ce qui permet de filtrer « Liste An » sur
la carte et d'y voir les 62 employeurs, pas seulement les nouveaux.
"""

from __future__ import annotations

import csv
from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from ananas import seed as seed_mod
from ananas.db import Base
from ananas.models import Company

FIELDS = ["slug", "name", "type", "city", "country", "website", "careers_url", "tags", "source"]


@pytest.fixture
def db(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    @contextmanager
    def scope():
        session = Session()
        try:
            yield session
            session.commit()
        finally:
            session.close()

    monkeypatch.setattr(seed_mod, "session_scope", scope)
    session = Session()
    yield session
    session.close()


def write_list(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({"country": "Belgium", "tags": "Liste An", "source": "liste-an", **row})
    return path


def test_merge_tags_ajoute_sans_doublon_ni_perte():
    assert seed_mod.merge_tags("", "Liste An") == "Liste An"
    assert seed_mod.merge_tags("Oncologie, liste an", "Liste An") == "Oncologie, liste an"
    assert seed_mod.merge_tags("Oncologie", "Liste An") == "Oncologie, Liste An"


def test_une_fiche_nouvelle_est_creee_avec_son_slug_et_sa_page_carrieres(db, tmp_path):
    path = write_list(
        tmp_path / "l.csv",
        [{"slug": "zoetis-belgium", "name": "Zoetis Belgium", "city": "Zaventem",
          "careers_url": "https://example.com/jobs"}],
    )
    assert seed_mod.seed([path]) == (1, 0, 0)

    company = db.scalar(select(Company).where(Company.slug == "zoetis-belgium"))
    assert company.source == "liste-an"
    assert company.tags == "Liste An"
    assert company.careers_url == "https://example.com/jobs"


def test_une_fiche_existante_recoit_le_tag_et_rien_d_autre(db, tmp_path):
    db.add(Company(slug="bioxodes", name="Bioxodes", source="biopark", city="Charleroi",
                   tags="", careers_url=""))
    db.commit()
    path = write_list(
        tmp_path / "l.csv",
        [{"slug": "bioxodes", "name": "Bioxodes SA", "city": "Gosselies",
          "careers_url": "https://example.com"}],
    )

    assert seed_mod.seed([path], update=True) == (0, 1, 0)
    db.expire_all()
    company = db.scalar(select(Company).where(Company.slug == "bioxodes"))
    assert (company.source, company.name, company.city) == ("biopark", "Bioxodes", "Charleroi")
    assert company.careers_url == ""
    assert company.tags == "Liste An"
    assert db.scalar(select(Company).where(Company.slug != "bioxodes")) is None


def test_la_relance_est_idempotente(db, tmp_path):
    db.add(Company(slug="sciensano", name="Sciensano", source="from_user", tags="Sante"))
    db.commit()
    path = write_list(
        tmp_path / "l.csv",
        [{"slug": "sciensano", "name": "Sciensano"}, {"slug": "fnrs", "name": "FNRS"}],
    )

    assert seed_mod.seed([path]) == (1, 1, 0)
    assert seed_mod.seed([path]) == (0, 0, 2)
    db.expire_all()
    tags = db.scalar(select(Company.tags).where(Company.slug == "sciensano"))
    assert tags == "Sante, Liste An"
