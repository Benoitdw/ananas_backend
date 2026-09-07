"""Garde-fou contre le masquage des constantes de classe d'un scraper.

``BaseScraper.__init__`` pose ``self.company`` (l'entreprise du repertoire) et
``self.session``. Une sous-classe qui declare une constante du meme nom la voit
donc ecrasee des que le worker instancie le scraper — mais *pas* en test, ou on
instancie sans entreprise. C'est exactement ce qui est arrive au scraper Sobi:
``company = "Sobi"`` partait dans l'URL SmartRecruiters sous la forme
``<ananas.models.Company object at 0x...>``, en production uniquement.

Le test instancie donc chaque scraper enregistre *avec* une entreprise, comme
le worker, et verifie que ses constantes de classe ont survecu.
"""

from __future__ import annotations

import pytest

from ananas.models import Company
from ananas.scrapers.base import BaseScraper
from ananas.scrapers.registry import load_scrapers

# Pose par __init__, donc impossible a utiliser comme constante de classe.
# `careers_url` n'y est pas: son ecrasement par la valeur en base est voulu.
RESERVED = ("company", "session")


@pytest.fixture(scope="module")
def scrapers() -> dict[str, type[BaseScraper]]:
    return load_scrapers()


def test_aucun_scraper_ne_declare_un_nom_reserve(scrapers):
    faute = [
        f"{cls.__module__}.{cls.__name__}.{name}"
        for cls in scrapers.values()
        for name in RESERVED
        # vars() et non getattr(): on ne veut que ce que la classe declare
        # elle-meme ou herite d'une base d'ATS, pas l'attribut de BaseScraper.
        if any(name in vars(ancestor) for ancestor in cls.__mro__ if ancestor is not BaseScraper)
    ]
    assert faute == [], (
        "constantes de classe masquees par BaseScraper.__init__: "
        + ", ".join(faute)
        + " — prefixe-les (voir sr_company dans smartrecruiters.py)"
    )


def test_les_constantes_survivent_a_l_instanciation_avec_entreprise(scrapers):
    """Le worker instancie `scraper_cls(company)`: c'est ce cas qu'on couvre."""
    company = Company(id=1, slug="acme", name="Acme", careers_url="")

    for key, cls in scrapers.items():
        avant = {
            name: value
            for name, value in vars(cls).items()
            if isinstance(value, (str, int, float, frozenset)) and not name.startswith("__")
        }
        instance = cls(company)
        for name, value in avant.items():
            assert getattr(instance, name) == value, (
                f"{key}: la constante '{name}' vaut {getattr(instance, name)!r} "
                f"une fois instanciee, au lieu de {value!r}"
            )
