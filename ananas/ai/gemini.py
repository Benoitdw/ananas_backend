"""Fournisseur Gemini (API Google AI Studio).

Utilise la generation contrainte par schema (``responseSchema``): le modele ne
peut pas produire autre chose que le JSON attendu, ce qui evite d'avoir a
reparer des reponses mal formees.
"""

from __future__ import annotations

import json
import logging
from base64 import b64encode
from typing import Any

import requests

from ananas.ai.base import BaseLLM, LLMError
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
