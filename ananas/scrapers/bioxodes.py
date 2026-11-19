"""Bioxodes — Gosselies. Offres publiees sur biopark.jobs uniquement.

La page carrieres de Bioxodes ne liste rien: son bouton « Apply now » pointe
vers sa fiche employeur ``biopark.jobs/en/company/4438``.

Verifie le 2026-11-19: 0 offre (candidature spontanee seulement).
"""

from __future__ import annotations

from ananas.scrapers.bioparkjobs import BioparkJobsScraper
from ananas.scrapers.registry import register


@register
class BioxodesScraper(BioparkJobsScraper):
    key = "bioxodes"
    label = "Bioxodes"
    bp_employer = "bioxodes"
    careers_url = "https://bioxodes.com/careers"
