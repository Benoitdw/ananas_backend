"""Classe parente de tous les canaux de notification.

Ajouter un transport (email, Discord, webhook, push) = creer un fichier dans
ce package, sous-classer ``BaseNotifier``, le decorer avec ``@register``.
Le worker n'a pas a etre modifie: il resout le notifier depuis
``NotificationChannel.type``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar


class NotifierError(RuntimeError):
    """Echec d'envoi. Capture par le worker: l'offre ne sera pas marquee comme
    notifiee et sera donc retentee au prochain run."""


@dataclass
class JobLine:
    """Une ligne d'offre a afficher dans un message."""

    title: str
    url: str
    location: str | None = None
    # Score de correspondance 0-100, None si l'utilisateur n'a pas de profil
    # ou si l'offre n'est pas encore caracterisee
    score: int | None = None


@dataclass
class Digest:
    """Contenu d'une notification, independant du transport.

    Chaque notifier le rend dans son propre format (HTML Telegram, texte brut,
    corps d'email...) — la mise en forme n'a pas a etre dupliquee dans le worker.
    """

    # {nom de l'entreprise: [offres]}, dans l'ordre d'affichage voulu
    companies: dict[str, list[JobLine]]

    @property
    def job_count(self) -> int:
        return sum(len(jobs) for jobs in self.companies.values())


class BaseNotifier(ABC):
    # Cle du transport, stockee dans notification_channels.type
    type: ClassVar[str]
    # Libelle lisible, affiche dans l'interface
    label: ClassVar[str] = ""

    @abstractmethod
    def send(self, target: str, digest: Digest) -> None:
        """Envoie le digest a la cible. Lever NotifierError en cas d'echec."""

    @abstractmethod
    def send_test(self, target: str) -> None:
        """Message de verification, declenche depuis la page Parametres.

        C'est le seul moyen pour un utilisateur de valider qu'il a colle le bon
        identifiant avant d'attendre 24h une notification qui n'arrivera pas.
        """

    @abstractmethod
    def validate_target(self, target: str) -> bool:
        """Validation de forme de l'identifiant, sans appel reseau."""

    def is_configured(self) -> bool:
        """False si le transport manque de configuration serveur (token absent).

        Permet a l'interface de le signaler plutot que d'echouer a l'envoi.
        """
        return True
