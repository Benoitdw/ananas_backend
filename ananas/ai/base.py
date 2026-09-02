"""Fournisseur de modele de langage.

Une seule capacite est demandee: transformer un texte libre en JSON conforme a
un schema. C'est volontairement etroit — tout le reste du systeme (le calcul de
correspondance) est du Python deterministe.

Consequence: passer a un modele local ne demande qu'une nouvelle sous-classe
ici. Le scoring, les modeles de donnees, le worker et l'interface ne bougent
pas. C'est aussi ce qui evite un cout en N_utilisateurs x N_offres: le LLM ne
sert qu'a structurer, jamais a comparer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar


class LLMError(RuntimeError):
    """Echec d'appel au modele. Capture par les appelants: une extraction
    ratee laisse l'offre sans caracteristiques, elle sera retentee."""


class BaseLLM(ABC):
    # Cle du fournisseur, valeur de AI_PROVIDER
    key: ClassVar[str]
    label: ClassVar[str] = ""

    @abstractmethod
    def complete_json(
        self, *, system: str, prompt: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        """Retourne un objet JSON conforme a ``schema``.

        ``schema`` suit la forme JSON Schema (type/properties/items/enum). Les
        fournisseurs qui savent contraindre la generation doivent le faire;
        les autres doivent au minimum valider et lever LLMError.
        """

    @abstractmethod
    def is_configured(self) -> bool:
        """False si la configuration serveur manque (cle absente)."""

    def read_document(self, *, data: bytes, mime_type: str, instruction: str) -> str:
        """Transcrit un document binaire (PDF scanne) en texte.

        Capacite **optionnelle**: sert uniquement de repli quand un PDF n'a
        aucune couche texte. Un fournisseur qui ne sait pas le faire laisse
        cette implementation lever, et l'appelant demande alors a
        l'utilisateur de coller son texte. Un modele local sans entree
        documentaire reste donc parfaitement utilisable.
        """
        raise NotImplementedError(f"{self.describe()} ne sait pas lire un document")

    def describe(self) -> str:
        return self.label or self.key
