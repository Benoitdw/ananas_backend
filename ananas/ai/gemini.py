"""Fournisseur Gemini (API Google AI Studio).

Utilise la generation contrainte par schema (``responseSchema``): le modele ne
peut pas produire autre chose que le JSON attendu, ce qui evite d'avoir a
reparer des reponses mal formees.

Deux modes d'appel: ``complete_json`` en temps reel (chaque appel = une
requete HTTP, un resultat immediat), et ``submit_batch``/``poll_batch`` en
mode lot — l'API ``batchGenerateContent`` de Gemini, a moitie prix mais sans
delai garanti (cible 24h, souvent bien plus rapide). Voir
``ananas.ai.service`` pour l'usage: l'extraction des offres passe par le lot,
l'extraction d'un profil (attendue en direct par l'utilisateur) reste en
temps reel.
"""

from __future__ import annotations

import json
import logging
from base64 import b64encode
from datetime import UTC, datetime
from typing import Any

import requests

from ananas.ai.base import BaseLLM, BatchItem, BatchPoll, LLMError
from ananas.ai.registry import register
from ananas.config import settings

log = logging.getLogger(__name__)

API_ROOT = "https://generativelanguage.googleapis.com/v1beta"

# Champs JSON Schema que l'API Gemini ne comprend pas
_UNSUPPORTED = {"additionalProperties", "$schema", "title", "default"}


def _to_gemini_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Elague les mots-cles JSON Schema non supportes par responseSchema."""
    if not isinstance(schema, dict):
        return schema
    out: dict[str, Any] = {}
    for key, value in schema.items():
        if key in _UNSUPPORTED:
            continue
        if key == "properties":
            out[key] = {k: _to_gemini_schema(v) for k, v in value.items()}
        elif key == "items":
            out[key] = _to_gemini_schema(value)
        else:
            out[key] = value
    return out


@register
class GeminiLLM(BaseLLM):
    key = "gemini"
    label = "Google Gemini"

    def is_configured(self) -> bool:
        return bool(settings.gemini_api_key)

    def read_document(self, *, data: bytes, mime_type: str, instruction: str) -> str:
        """Gemini accepte un PDF en entree: c'est ce qui permet de recuperer un
        CV scanne, pour lequel aucune couche texte n'existe."""
        if not self.is_configured():
            raise LLMError("GEMINI_API_KEY n'est pas configure cote serveur")

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"inlineData": {"mimeType": mime_type, "data": b64encode(data).decode()}},
                        {"text": instruction},
                    ],
                }
            ],
            "generationConfig": {"temperature": 0},
        }
        return self._text(f"{API_ROOT}/models/{settings.ai_model}:generateContent", payload)

    def complete_json(self, *, system: str, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        if not self.is_configured():
            raise LLMError("GEMINI_API_KEY n'est pas configure cote serveur")

        url = f"{API_ROOT}/models/{settings.ai_model}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": _to_gemini_schema(schema),
                # Extraction factuelle: on ne veut pas de variabilite entre
                # deux passages sur la meme offre.
                "temperature": 0,
            },
        }

        text = self._text(url, payload)
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMError(f"Gemini n'a pas renvoye du JSON: {text[:300]}") from exc

    # -------------------------------------------------------------- mode lot

    def supports_batch(self) -> bool:
        return True

    def submit_batch(self, items: list[BatchItem]) -> str:
        """Soumet toutes les requetes en un seul appel ``batchGenerateContent``.

        En mode "inline" (< 20 Mo, largement suffisant pour un lot d'offres
        d'emploi textuelles), chaque requete garde sa propre systemInstruction
        et son propre responseSchema — exactement comme un ``generateContent``
        individuel. Les reponses reviennent alignees par position sur cette
        meme liste (voir ``poll_batch``), pas par la cle ``metadata.key``
        (qui n'est fiable que pour les lots soumis via un fichier JSONL).
        """
        if not self.is_configured():
            raise LLMError("GEMINI_API_KEY n'est pas configure cote serveur")
        if not items:
            raise LLMError("Lot vide")

        url = f"{API_ROOT}/models/{settings.ai_model}:batchGenerateContent"
        payload = {
            "batch": {
                "display_name": f"ananas-extraction-{datetime.now(UTC):%Y%m%d-%H%M%S}",
                "input_config": {
                    "requests": {
                        "requests": [
                            {
                                "request": {
                                    "systemInstruction": {"parts": [{"text": item.system}]},
                                    "contents": [{"role": "user", "parts": [{"text": item.prompt}]}],
                                    "generationConfig": {
                                        "responseMimeType": "application/json",
                                        "responseSchema": _to_gemini_schema(item.schema),
                                        "temperature": 0,
                                    },
                                },
                                "metadata": {"key": str(index)},
                            }
                            for index, item in enumerate(items)
                        ]
                    }
                },
            }
        }

        try:
            response = requests.post(
                url,
                params={"key": settings.gemini_api_key},
                json=payload,
                timeout=settings.ai_timeout,
            )
        except requests.RequestException as exc:
            raise LLMError(f"Gemini injoignable (soumission du lot): {exc}") from exc

        if response.status_code != 200:
            raise LLMError(
                f"Gemini a refuse la soumission du lot ({response.status_code}): "
                f"{response.text[:300]}"
            )

        name = response.json().get("name")
        if not name:
            raise LLMError(f"Reponse de soumission inexploitable: {response.text[:300]}")
        return name

    def poll_batch(self, batch_id: str) -> BatchPoll:
        if not self.is_configured():
            raise LLMError("GEMINI_API_KEY n'est pas configure cote serveur")

        try:
            response = requests.get(
                f"{API_ROOT}/{batch_id}", params={"key": settings.gemini_api_key}, timeout=30
            )
        except requests.RequestException as exc:
            raise LLMError(f"Gemini injoignable (lot {batch_id}): {exc}") from exc

        if response.status_code != 200:
            raise LLMError(
                f"Gemini a repondu {response.status_code} pour le lot {batch_id}: "
                f"{response.text[:300]}"
            )

        data = response.json()
        state = batch_state(data)

        if state in ("", "PENDING", "RUNNING"):
            return BatchPoll(state="pending")

        if state != "SUCCEEDED":
            # FAILED / CANCELLED / EXPIRED: le lot entier est perdu. Les offres
            # concernees restent sans caracteristiques et repartiront dans le
            # prochain lot soumis.
            log.warning("lot Gemini %s termine en %s", batch_id, state)
            return BatchPoll(state="failed")

        results: list[dict[str, Any] | None] = []
        for entry in find_inlined_responses(data) or []:
            resp = entry.get("response") if isinstance(entry, dict) else None
            if not resp:
                results.append(None)
                continue
            try:
                results.append(json.loads(_answer_text(resp)))
            except (KeyError, IndexError, TypeError, ValueError):
                results.append(None)

        if not results:
            # Termine, mais rien de lisible: signaler plutot que de recolter un
            # lot vide, ce qui marquerait les offres comme traitees a tort.
            log.warning(
                "lot Gemini %s reussi mais sans reponse inline exploitable: %s",
                batch_id, str(data)[:300],
            )
            return BatchPoll(state="failed")

        return BatchPoll(state="succeeded", results=results)

    def _text(self, url: str, payload: dict) -> str:
        """Appel brut, retourne la partie textuelle de la reponse."""
        try:
            response = requests.post(
                url,
                params={"key": settings.gemini_api_key},
                json=payload,
                timeout=settings.ai_timeout,
            )
        except requests.RequestException as exc:
            raise LLMError(f"Gemini injoignable: {exc}") from exc

        if response.status_code != 200:
            raise LLMError(f"Gemini a repondu {response.status_code}: {response.text[:300]}")

        try:
            return _answer_text(response.json())
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            # Reponse tronquee, filtre de securite, quota: on remonte la cause
            raise LLMError(f"Reponse Gemini inexploitable: {response.text[:300]}") from exc


def _answer_text(payload: dict[str, Any]) -> str:
    """Le texte de la reponse, parties de raisonnement exclues.

    Les modeles a raisonnement peuvent renvoyer des parties marquees
    ``thought``: les concatener avec la reponse produirait un JSON invalide,
    et donc une offre silencieusement non caracterisee. Elles ne sont
    normalement rendues que sur demande (``includeThoughts``), mais l'oubli
    couterait un lot entier — la garde est gratuite.
    """
    parts = payload["candidates"][0]["content"]["parts"]
    return "".join(part.get("text", "") for part in parts if not part.get("thought"))


# --------------------------------------------------- lecture d'une reponse de lot
# GET /v1beta/batches/{id} ne renvoie pas la meme forme selon la version de
# l'API et selon qu'on passe par le SDK ou par REST: le SDK expose un objet
# plat (`state`, `dest.inlinedResponses`), REST renvoie un
# `google.longrunning.Operation` qui range l'etat dans `metadata.state` ou
# `response.state`, et les reponses sous `response.output.inlinedResponses.
# inlinedResponses`. Les deux vocabulaires d'etat coexistent aussi
# (`JOB_STATE_*` cote SDK, `BATCH_STATE_*` cote REST).
#
# Lire une seule de ces formes, c'est ce qui laissait un lot "en cours" pour
# toujours: `data["state"]` absent valait "pas encore fini", et ses offres
# etaient exclues de tout nouveau lot. On accepte donc les deux formes plutot
# que de parier sur celle du jour.

_STATE_PREFIXES = ("JOB_STATE_", "BATCH_STATE_")


def batch_state(data: dict[str, Any]) -> str:
    """Etat du lot, sans son prefixe: 'PENDING', 'SUCCEEDED', 'FAILED'...

    Chaine vide quand aucun etat n'est lisible et que rien n'indique la fin —
    l'appelant traite ce cas comme "pas encore termine".
    """
    for holder in (data, data.get("metadata"), data.get("response")):
        if isinstance(holder, dict) and isinstance(state := holder.get("state"), str) and state:
            for prefix in _STATE_PREFIXES:
                if state.startswith(prefix):
                    return state[len(prefix) :]
            return state

    # Operation sans etat explicite: `done` fait foi, et la presence de `error`
    # distingue un echec d'une reussite.
    if data.get("done"):
        return "FAILED" if data.get("error") else "SUCCEEDED"
    return ""


def find_inlined_responses(node: Any) -> list | None:
    """Premiere liste `inlinedResponses` trouvee dans la reponse.

    Une recherche plutot qu'un chemin en dur: l'API imbrique cette liste a une
    profondeur qui a deja change (`dest.` cote SDK, `response.output.` cote
    REST, avec un objet homonyme qui enveloppe parfois la liste).
    """
    if isinstance(node, dict):
        value = node.get("inlinedResponses")
        if isinstance(value, list):
            return value
        # Certaines versions emballent la liste dans un objet du meme nom
        if isinstance(value, dict) and isinstance(inner := value.get("inlinedResponses"), list):
            return inner
        for child in node.values():
            if (found := find_inlined_responses(child)) is not None:
                return found
    elif isinstance(node, list):
        for child in node:
            if (found := find_inlined_responses(child)) is not None:
                return found
    return None
