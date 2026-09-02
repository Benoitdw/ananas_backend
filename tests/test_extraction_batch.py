"""Orchestration du mode lot: soumission et recolte (``ananas.ai.service``).

Le fournisseur est remplace par un faux (meme idiome que
``tests/test_cv_import.py``): ce qui est verrouille ici, c'est ce que le
service fait de ses reponses — pas l'API Gemini elle-meme (voir
``tests/test_gemini_batch.py``).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from ananas.ai import service
from ananas.ai.base import BaseLLM, BatchItem, BatchPoll
from ananas.db import Base
from ananas.models import Company, ExtractionBatch, Job, JobFeatures

RESULT = {
    "role_family": "data",
    "seniority": "senior",
    "years_experience_min": 3,
    "contract": "cdi",
    "remote": "hybride",
    "skills": ["python"],
    "nice_to_have": [],
    "domains": [],
    "languages": ["fr"],
    "locations": ["bruxelles"],
    "summary": "Une offre.",
}


class FakeLLM(BaseLLM):
    key = "fake"

    def __init__(self, *, batch=True, configured=True, submit_id="batches/1", poll=None):
        self._batch = batch
        self._configured = configured
        self.submit_id = submit_id
        self.poll_result = poll
        self.submitted_items: list[BatchItem] | None = None

    def is_configured(self) -> bool:
        return self._configured

    def supports_batch(self) -> bool:
        return self._batch

    def complete_json(self, *, system, prompt, schema):
        raise NotImplementedError

    def submit_batch(self, items: list[BatchItem]) -> str:
        self.submitted_items = items
        return self.submit_id

    def poll_batch(self, batch_id: str) -> BatchPoll:
        return self.poll_result


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


_counter = iter(range(1, 10_000))


def make_job(db, company=None, **kwargs) -> Job:
    n = next(_counter)
    company = company or Company(slug=f"c{n}", name="Acme", scraper_key=f"acme-{n}")
    if company.id is None:
        db.add(company)
        db.flush()
    job = Job(
        company_id=company.id,
        fingerprint=kwargs.pop("fingerprint", f"fp-{n}"),
        title=kwargs.pop("title", "Data Engineer"),
        url=kwargs.pop("url", f"https://acme.example/jobs/{n}"),
        **kwargs,
    )
    db.add(job)
    db.commit()
    return job


def fake_provider(monkeypatch, llm: FakeLLM):
    monkeypatch.setattr(service, "get_provider", lambda: llm)


# ------------------------------------------------------------- submit_batch


def test_rien_a_soumettre_rend_none(db, monkeypatch):
    fake_provider(monkeypatch, FakeLLM())
    assert service.submit_extraction_batch(db) is None


def test_fournisseur_sans_lot_rend_none(db, monkeypatch):
    make_job(db)
    fake_provider(monkeypatch, FakeLLM(batch=False))
    assert service.submit_extraction_batch(db) is None


def test_soumet_toutes_les_offres_manquantes(db, monkeypatch):
    j1 = make_job(db, title="Data Engineer")
    j2 = make_job(db, title="Data Scientist", fingerprint="fp-2")
    llm = FakeLLM()
    fake_provider(monkeypatch, llm)

    batch = service.submit_extraction_batch(db)

    assert batch is not None
    assert set(batch.job_ids) == {j1.id, j2.id}
    assert batch.status == "pending"
    assert len(llm.submitted_items) == 2
    assert db.get(ExtractionBatch, batch.id) is not None


def test_exclut_les_offres_deja_dans_un_lot_en_attente(db, monkeypatch):
    j1 = make_job(db, title="Deja en vol")
    db.add(ExtractionBatch(provider="fake", provider_batch_id="batches/old", job_ids=[j1.id]))
    db.commit()

    j2 = make_job(db, title="Nouvelle offre", fingerprint="fp-new")
    llm = FakeLLM()
    fake_provider(monkeypatch, llm)

    batch = service.submit_extraction_batch(db)

    assert batch.job_ids == [j2.id]


def test_ne_leve_pas_si_la_soumission_echoue(db, monkeypatch):
    from ananas.ai.base import LLMError

    make_job(db)

    class Refuse(FakeLLM):
        def submit_batch(self, items):
            raise LLMError("quota depasse")

    fake_provider(monkeypatch, Refuse())
    assert service.submit_extraction_batch(db) is None
    assert db.scalars(select(ExtractionBatch)).first() is None


# ------------------------------------------------------------- collect_batch


def test_lot_pas_termine_ne_touche_a_rien(db, monkeypatch):
    j1 = make_job(db)
    db.add(ExtractionBatch(provider="fake", provider_batch_id="batches/1", job_ids=[j1.id]))
    db.commit()

    fake_provider(monkeypatch, FakeLLM(poll=BatchPoll(state="pending")))

    assert service.collect_extraction_batches(db) == 0
    batch = db.scalars(select(ExtractionBatch)).one()
    assert batch.status == "pending"
    assert db.get(JobFeatures, j1.id) is None


def test_lot_reussi_applique_les_resultats_et_tolere_un_echec_isole(db, monkeypatch):
    j1 = make_job(db, title="Reussie", fingerprint="fp-ok")
    j2 = make_job(db, title="Echouee au sein du lot", fingerprint="fp-ko")
    db.add(
        ExtractionBatch(
            provider="fake", provider_batch_id="batches/1", job_ids=[j1.id, j2.id]
        )
    )
    db.commit()

    poll = BatchPoll(state="succeeded", results=[RESULT, None])
    fake_provider(monkeypatch, FakeLLM(poll=poll))

    done = service.collect_extraction_batches(db)

    assert done == 1
    features = db.get(JobFeatures, j1.id)
    assert features is not None
    assert features.role_family == "data"
    assert db.get(JobFeatures, j2.id) is None  # repart dans le prochain lot

    batch = db.scalars(select(ExtractionBatch)).one()
    assert batch.status == "collected"
    assert batch.collected_at is not None


def test_lot_echoue_marque_le_lot_failed(db, monkeypatch):
    j1 = make_job(db)
    db.add(ExtractionBatch(provider="fake", provider_batch_id="batches/1", job_ids=[j1.id]))
    db.commit()

    fake_provider(monkeypatch, FakeLLM(poll=BatchPoll(state="failed")))

    assert service.collect_extraction_batches(db) == 0
    batch = db.scalars(select(ExtractionBatch)).one()
    assert batch.status == "failed"


def test_offre_fermee_entre_temps_est_ignoree_sans_erreur(db, monkeypatch):
    j1 = make_job(db)
    db.add(ExtractionBatch(provider="fake", provider_batch_id="batches/1", job_ids=[j1.id]))
    db.commit()
    j1.closed_at = datetime.now(UTC)
    db.commit()

    poll = BatchPoll(state="succeeded", results=[RESULT])
    fake_provider(monkeypatch, FakeLLM(poll=poll))

    assert service.collect_extraction_batches(db) == 0
    assert db.get(JobFeatures, j1.id) is None
