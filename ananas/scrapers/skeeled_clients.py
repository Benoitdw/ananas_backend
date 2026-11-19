"""Deux entreprises qui publient via Skeeled (voir ``skeeled.py``).

- **CHU UCL Namur** (Godinne, Dinant, Sainte-Elisabeth): la page WordPress
  ``emploi.chuuclnamur.be/nos-offres-demploi/`` liste toutes les offres.
- **Bepharbel Manufacturing** (Courcelles): ``/offres-emploi/``. Le seul lien
  Skeeled publie au 2026-11-19 est la candidature spontanee, ignoree.

Verifie le 2026-11-19: 24 offres (CHU UCL Namur), 0 (Bepharbel).
"""

from __future__ import annotations

from ananas.scrapers.registry import register
from ananas.scrapers.skeeled import SkeeledScraper


@register
class CHUUCLNamurScraper(SkeeledScraper):
    key = "chu-ucl-namur"
    label = "CHU UCL Namur"
    careers_url = "https://emploi.chuuclnamur.be/nos-offres-demploi/"


@register
class BepharbelScraper(SkeeledScraper):
    key = "bepharbel"
    label = "Bepharbel Manufacturing"
    careers_url = "https://www.bepharbel.com/offres-emploi/"
    ignore_ids = frozenset({"65e883fb721d339c3ad65b51"})  # candidature spontanee
