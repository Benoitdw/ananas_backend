"""Registre des notifiers, sur le meme modele que celui des scrapers."""

from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import TypeVar

from ananas.notifiers.base import BaseNotifier

log = logging.getLogger(__name__)

NOTIFIERS: dict[str, BaseNotifier] = {}

T = TypeVar("T", bound=type[BaseNotifier])


def register(cls: T) -> T:
    """Instancie et enregistre un notifier. Les notifiers sont sans etat:
    une instance partagee suffit."""
    key = getattr(cls, "type", None)
    if not key:
        raise ValueError(f"{cls.__name__} doit definir un attribut de classe `type`")
    NOTIFIERS[key] = cls()
    return cls


def load_notifiers() -> dict[str, BaseNotifier]:
    import ananas.notifiers as pkg

    for mod in pkgutil.iter_modules(pkg.__path__):
        if mod.name in {"base", "registry"} or mod.name.startswith("_"):
            continue
        try:
            importlib.import_module(f"{pkg.__name__}.{mod.name}")
        except Exception as exc:  # noqa: BLE001
            log.error("notifier '%s' non chargeable: %s", mod.name, exc)
    return NOTIFIERS


def get_notifier(type_: str) -> BaseNotifier | None:
    if not NOTIFIERS:
        load_notifiers()
    return NOTIFIERS.get(type_)


def available_types() -> list[str]:
    if not NOTIFIERS:
        load_notifiers()
    return sorted(NOTIFIERS)
