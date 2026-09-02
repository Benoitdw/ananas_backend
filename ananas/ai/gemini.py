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
        state = data.get("state", "")

        if state in ("", "JOB_STATE_PENDING", "JOB_STATE_RUNNING"):
            return BatchPoll(state="pending")

        if state != "JOB_STATE_SUCCEEDED":
            # JOB_STATE_FAILED / CANCELLED / EXPIRED: le lot entier est perdu.
            # Les offres concernees restent sans caracteristiques et
            # repartiront dans le prochain lot soumis.
            log.warning("lot Gemini %s termine en %s", batch_id, state)
            return BatchPoll(state="failed")

        inlined = ((data.get("dest") or {}).get("inlinedResponses")) or []
        results: list[dict[str, Any] | None] = []
        for entry in inlined:
            resp = entry.get("response")
            if not resp:
                results.append(None)
                continue
            try:
                parts = resp["candidates"][0]["content"]["parts"]
                text = "".join(part.get("text", "") for part in parts)
                results.append(json.loads(text))
            except (KeyError, IndexError, TypeError, ValueError):
                results.append(None)
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
            parts = response.json()["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError, ValueError) as exc:
            # Reponse tronquee, filtre de securite, quota: on remonte la cause
            raise LLMError(f"Reponse Gemini inexploitable: {response.text[:300]}") from exc

        return "".join(part.get("text", "") for part in parts)
