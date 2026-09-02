"""Registre des scrapers.

Deposer un fichier dans ce package suffit: ``load_scrapers()`` importe tous les
modules du package au demarrage, ce qui declenche les decorateurs ``@register``.
Aucune liste a maintenir a la main.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import TypeVar

from ananas.scrapers.base import BaseScraper

log = logging.getLogger(__name__)

SCRAPERS: dict[str, type[BaseScraper]] = {}

T = TypeVar("T", bound=type[BaseScraper])


def register(cls: T) -> T:
    """Decorateur a poser sur chaque sous-classe concrete de BaseScraper."""
    key = getattr(cls, "key", None)
    if not key:
        raise ValueError(f"{cls.__name__} doit definir un attribut de classe `key`")
    if key in SCRAPERS and SCRAPERS[key] is not cls:
        raise ValueError(f"cle de scraper dupliquee: '{key}' ({cls.__name__})")
    SCRAPERS[key] = cls
    return cls


def load_scrapers() -> dict[str, type[BaseScraper]]:
    """Importe tous les modules du package pour peupler SCRAPERS. Idempotent."""
    import ananas.scrapers as pkg

    for mod in pkgutil.iter_modules(pkg.__path__):
        if mod.name in {"base", "registry", "http"} or mod.name.startswith("_"):
            continue
        try:
            importlib.import_module(f"{pkg.__name__}.{mod.name}")
        except Exception as exc:  # noqa: BLE001
            # Un scraper casse ne doit pas empecher les autres de tourner
            log.error("scraper '%s' non chargeable: %s", mod.name, exc)
    return SCRAPERS


def get_scraper(key: str) -> type[BaseScraper] | None:
    if not SCRAPERS:
        load_scrapers()
    return SCRAPERS.get(key)
