"""Mode lot de GeminiLLM: soumission et recolte d'un ``batchGenerateContent``.

Aucun appel reseau reel: ``requests.post``/``requests.get`` sont remplaces par
des reponses fabriquees, sur le meme modele que le service Telegram
(``tests/test_telegram_link.py``). Ce qui est verrouille ici, c'est le contrat
avec l'API — payload envoye, etats possibles, alignement des reponses par
position — pas la disponibilite du service Google.
"""

from __future__ import annotations

import pytest

from ananas.ai.base import BatchItem, LLMError
from ananas.ai.gemini import GeminiLLM
from ananas.config import settings


class FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)[:500]

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")


@pytest.fixture
def llm():
    return GeminiLLM()


def two_items():
    return [
        BatchItem(system="sys-1", prompt="prompt-1", schema={"type": "object"}),
        BatchItem(system="sys-2", prompt="prompt-2", schema={"type": "object"}),
    ]


# --------------------------------------------------------------- submit_batch


def test_submit_batch_envoie_une_requete_par_item_alignee_par_position(monkeypatch):
    captured = {}

    def fake_post(url, params, json, timeout):
        captured["url"] = url
        captured["payload"] = json
        return FakeResponse(200, {"name": "batches/abc123"})

    monkeypatch.setattr("ananas.ai.gemini.requests.post", fake_post)

    batch_id = GeminiLLM().submit_batch(two_items())

    assert batch_id == "batches/abc123"
    assert captured["url"].endswith(":batchGenerateContent")
    requests_sent = captured["payload"]["batch"]["input_config"]["requests"]["requests"]
    assert len(requests_sent) == 2
    # metadata.key suit l'ordre de soumission: c'est cet ordre, pas la cle,
    # qui sert a reassocier les reponses inline (voir poll_batch)
    assert [r["metadata"]["key"] for r in requests_sent] == ["0", "1"]
    first = requests_sent[0]["request"]
    assert first["systemInstruction"]["parts"][0]["text"] == "sys-1"
    assert first["contents"][0]["parts"][0]["text"] == "prompt-1"
    assert first["generationConfig"]["responseMimeType"] == "application/json"


def test_submit_batch_lot_vide_refuse(llm):
    with pytest.raises(LLMError):
        llm.submit_batch([])


def test_submit_batch_sans_cle_configuree(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    with pytest.raises(LLMError):
        GeminiLLM().submit_batch(two_items())


def test_submit_batch_echec_http(monkeypatch, llm):
    monkeypatch.setattr(
        "ananas.ai.gemini.requests.post",
        lambda *a, **k: FakeResponse(429, {"error": "quota"}),
    )
    with pytest.raises(LLMError):
        llm.submit_batch(two_items())


def test_submit_batch_reponse_sans_name(monkeypatch, llm):
    monkeypatch.setattr(
        "ananas.ai.gemini.requests.post", lambda *a, **k: FakeResponse(200, {})
    )
    with pytest.raises(LLMError):
        llm.submit_batch(two_items())


# ----------------------------------------------------------------- poll_batch


@pytest.mark.parametrize("state", ["JOB_STATE_PENDING", "JOB_STATE_RUNNING", ""])
def test_poll_batch_pas_termine(monkeypatch, llm, state):
    monkeypatch.setattr(
        "ananas.ai.gemini.requests.get",
        lambda *a, **k: FakeResponse(200, {"state": state}),
    )
    poll = llm.poll_batch("batches/abc123")
    assert poll.state == "pending"
    assert poll.results is None


@pytest.mark.parametrize("state", ["JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED"])
def test_poll_batch_lot_perdu(monkeypatch, llm, state):
    monkeypatch.setattr(
        "ananas.ai.gemini.requests.get",
        lambda *a, **k: FakeResponse(200, {"state": state}),
    )
    poll = llm.poll_batch("batches/abc123")
    assert poll.state == "failed"
    assert poll.results is None


def test_poll_batch_succes_aligne_par_position_et_tolere_un_echec_isole(monkeypatch, llm):
    """Deux requetes soumises, une reussit, une echoue au sein du meme lot:
    le lot est global "succeeded" mais results[1] doit rester None plutot que
    de faire echouer toute la recolte."""
    payload = {
        "state": "JOB_STATE_SUCCEEDED",
        "dest": {
            "inlinedResponses": [
                {
                    "response": {
                        "candidates": [
                            {"content": {"parts": [{"text": '{"role_family": "data"}'}]}}
                        ]
                    }
                },
                {"error": {"code": 500, "message": "internal"}},
            ]
        },
    }
    monkeypatch.setattr(
        "ananas.ai.gemini.requests.get", lambda *a, **k: FakeResponse(200, payload)
    )
    poll = llm.poll_batch("batches/abc123")
    assert poll.state == "succeeded"
    assert poll.results == [{"role_family": "data"}, None]


def test_poll_batch_json_illisible_devient_none(monkeypatch, llm):
    payload = {
        "state": "JOB_STATE_SUCCEEDED",
        "dest": {
            "inlinedResponses": [
                {"response": {"candidates": [{"content": {"parts": [{"text": "pas du json"}]}}]}}
            ]
        },
    }
    monkeypatch.setattr(
        "ananas.ai.gemini.requests.get", lambda *a, **k: FakeResponse(200, payload)
    )
    poll = llm.poll_batch("batches/abc123")
    assert poll.results == [None]


def test_supports_batch():
    assert GeminiLLM().supports_batch() is True
