"""Terumo Europe — site carrieres SAP SuccessFactors.

``careers.terumo-europe.com``, theme "tableau" (``tr.data-row``). Le siege
europeen et l'usine sont a Leuven ; le libelle de lieu de la liste est le pays
("Belgium"), d'ou le re-filtrage sur ``location_tokens``.

Verifie le 2026-09-02 : 14 offres en Belgique.
"""

from __future__ import annotations

from ananas.scrapers.registry import register
from ananas.scrapers.successfactors import SuccessFactorsScraper


@register
class TerumoEuropeScraper(SuccessFactorsScraper):
    key = "terumo-europe"
    label = "Terumo Europe"
    base_url = "https://careers.terumo-europe.com"
    careers_url = "https://careers.terumo-europe.com/search/?q=&locationsearch=Belgium"
