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
#
# GET /v1beta/batches/{id} n'a pas une seule forme. Le SDK expose un objet plat
# (`state`, `dest.inlinedResponses`); REST renvoie un `longrunning.Operation`
# qui range l'etat dans `metadata.state` et les reponses sous
# `response.output.inlinedResponses.inlinedResponses`. Les deux vocabulaires
# d'etat coexistent (`JOB_STATE_*` / `BATCH_STATE_*`).
#
# N'en lire qu'une, c'est ce qui laissait un lot "en cours" pour toujours:
# `data["state"]` absent valait "pas encore fini", et `submit_extraction_batch`
# excluant les offres d'un lot en cours, elles n'etaient plus jamais
# caracterisees. Les deux formes sont donc testees cote a cote.


def sdk_shape(state: str, inlined: list | None = None) -> dict:
    """Objet plat, tel que l'expose le SDK Python."""
    payload: dict = {"state": f"JOB_STATE_{state}"}
    if inlined is not None:
        payload["dest"] = {"inlinedResponses": inlined}
    return payload


def rest_shape(state: str, inlined: list | None = None) -> dict:
    """`longrunning.Operation` tel que le documente Google: resultats sous
    ``response.output.inlinedResponses.inlinedResponses``."""
    payload: dict = {
        "name": "batches/abc123",
        "metadata": {"state": f"BATCH_STATE_{state}"},
        "done": state not in ("PENDING", "RUNNING"),
    }
    if inlined is not None:
        payload["response"] = {"output": {"inlinedResponses": {"inlinedResponses": inlined}}}
    return payload


def live_shape(state: str, inlined: list | None = None) -> dict:
    """Ce que l'API renvoie *reellement* (releve le 2026-09-07 sur
    ``gemini-3.7-flash``): l'etat dans ``metadata.state``, et les resultats
    sous ``metadata.output.inlinedResponses.inlinedResponses`` — un troisieme
    chemin, qui n'est celui d'aucune des deux formes documentees.

    C'est la forme qui compte en production, et celle qu'aucun chemin en dur
    n'aurait trouvee. Elle est figee ici pour que le jour ou quelqu'un
    "simplifie" la recherche en un acces direct, le test tombe.
    """
    payload: dict = {
        "name": "batches/abc123",
        "metadata": {
            "@type": "type.googleapis.com/google.ai.generativelanguage.v1main.GenerateContentBatch",
            "model": "models/gemini-3.7-flash",
            "state": f"BATCH_STATE_{state}",
        },
    }
    if inlined is not None:
        payload["done"] = True
        payload["response"] = {"@type": "…GenerateContentBatch"}
        payload["metadata"]["output"] = {"inlinedResponses": {"inlinedResponses": inlined}}
    return payload


SHAPES = [sdk_shape, rest_shape, live_shape]


def responded(text: str, thought: str | None = None) -> dict:
    """Une reponse inline. ``thought`` ajoute une partie de raisonnement, que
    les modeles a raisonnement peuvent intercaler."""
    parts = [{"text": text, "thoughtSignature": "EuwGCukGARFNMg9r"}]
    if thought is not None:
        parts.insert(0, {"text": thought, "thought": True})
    return {"response": {"candidates": [{"content": {"parts": parts, "role": "model"}}]}}


def poll(monkeypatch, llm, payload):
    monkeypatch.setattr(
        "ananas.ai.gemini.requests.get", lambda *a, **k: FakeResponse(200, payload)
    )
    return llm.poll_batch("batches/abc123")


@pytest.mark.parametrize("shape", SHAPES)
@pytest.mark.parametrize("state", ["PENDING", "RUNNING"])
def test_poll_batch_pas_termine(monkeypatch, llm, shape, state):
    assert poll(monkeypatch, llm, shape(state)).state == "pending"


def test_poll_batch_etat_illisible_reste_en_attente(monkeypatch, llm):
    """Ni etat ni `done`: on ne conclut pas. Le garde-fou contre un lot qui ne
    finit jamais est ailleurs (``service.BATCH_MAX_AGE_HOURS``), pas dans une
    interpretation optimiste d'une reponse qu'on ne comprend pas."""
    assert poll(monkeypatch, llm, {"name": "batches/abc123"}).state == "pending"


@pytest.mark.parametrize("shape", SHAPES)
@pytest.mark.parametrize("state", ["FAILED", "CANCELLED", "EXPIRED"])
def test_poll_batch_lot_perdu(monkeypatch, llm, shape, state):
    result = poll(monkeypatch, llm, shape(state))
    assert result.state == "failed"
    assert result.results is None


def test_poll_batch_operation_terminee_en_erreur_sans_etat(monkeypatch, llm):
    payload = {"name": "batches/abc123", "done": True, "error": {"code": 13}}
    assert poll(monkeypatch, llm, payload).state == "failed"


@pytest.mark.parametrize("shape", SHAPES)
def test_poll_batch_succes_aligne_par_position_et_tolere_un_echec_isole(
    monkeypatch, llm, shape
):
    """Deux requetes soumises, une reussit, une echoue au sein du meme lot:
    le lot est global "succeeded" mais results[1] doit rester None plutot que
    de faire echouer toute la recolte."""
    payload = shape(
        "SUCCEEDED",
        [responded('{"role_family": "data"}'), {"error": {"code": 500, "message": "internal"}}],
    )
    result = poll(monkeypatch, llm, payload)
    assert result.state == "succeeded"
    assert result.results == [{"role_family": "data"}, None]


@pytest.mark.parametrize("shape", SHAPES)
def test_poll_batch_json_illisible_devient_none(monkeypatch, llm, shape):
    assert poll(monkeypatch, llm, shape("SUCCEEDED", [responded("pas du json")])).results == [None]


@pytest.mark.parametrize("shape", SHAPES)
def test_poll_batch_succes_sans_reponse_exploitable_est_un_echec(monkeypatch, llm, shape):
    """Recolter un lot vide marquerait ses offres comme traitees alors qu'elles
    n'ont rien recu: mieux vaut le declarer perdu et le resoumettre."""
    assert poll(monkeypatch, llm, shape("SUCCEEDED", [])).state == "failed"


def test_poll_batch_ignore_les_parties_de_raisonnement(monkeypatch, llm):
    """Concatener le raisonnement avec la reponse produirait un JSON invalide,
    donc une offre silencieusement non caracterisee."""
    payload = live_shape(
        "SUCCEEDED", [responded('{"role_family": "data"}', thought="Reflechissons…")]
    )
    assert poll(monkeypatch, llm, payload).results == [{"role_family": "data"}]


def test_supports_batch():
    assert GeminiLLM().supports_batch() is True
