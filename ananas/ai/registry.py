"""Registre des fournisseurs de modele, sur le meme modele que les scrapers."""

from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import TypeVar

from ananas.ai.base import BaseLLM
from ananas.config import settings

log = logging.getLogger(__name__)

PROVIDERS: dict[str, BaseLLM] = {}

T = TypeVar("T", bound=type[BaseLLM])


def register(cls: T) -> T:
    key = getattr(cls, "key", None)
    if not key:
        raise ValueError(f"{cls.__name__} doit definir un attribut de classe `key`")
    PROVIDERS[key] = cls()
    return cls


def load_providers() -> dict[str, BaseLLM]:
    import ananas.ai as pkg

    for mod in pkgutil.iter_modules(pkg.__path__):
        if mod.name in {"base", "registry", "extraction", "matching", "prompts"}:
            continue
        if mod.name.startswith("_"):
            continue
        try:
            importlib.import_module(f"{pkg.__name__}.{mod.name}")
        except Exception as exc:  # noqa: BLE001
            log.error("fournisseur '%s' non chargeable: %s", mod.name, exc)
    return PROVIDERS


def get_provider(key: str | None = None) -> BaseLLM | None:
    """Fournisseur demande, ou celui configure par AI_PROVIDER."""
    if not PROVIDERS:
        load_providers()
    return PROVIDERS.get(key or settings.ai_provider)


def available() -> list[str]:
    if not PROVIDERS:
        load_providers()
    return sorted(PROVIDERS)
