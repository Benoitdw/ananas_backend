"""Nelson Labs Europe — site carrieres Workday du groupe Sotera Health.

Nelson Labs (tests de sterilite / biocompatibilite) partage le portail Workday
de Sotera Health, qui heberge aussi Sterigenics et Nordion. Ce tenant n'expose
pas de facette pays : recherche texte ``"Belgium"`` puis double filtrage —
``country`` belge (JSON de detail) **et** libelle de lieu contenant "Leuven",
pour ne pas ramener les postes Sterigenics de Fleurus / Petit-Rechain qui ne
sont pas dans le repertoire.

Limite connue : le portail Sotera ne distingue pas Nelson Labs de Sterigenics,
tous deux a Leuven. Un poste "Leuven Sterigenics" est donc remonte sous Nelson
Labs — meme groupe, meme ville, profil proche ; le site propre de Nelson Labs
est inaccessible depuis le conteneur.

Verifie le 2026-09-02 : 1 offre (Leuven).
"""

from __future__ import annotations

from ananas.scrapers.registry import register
from ananas.scrapers.workday import WorkdayScraper


@register
class NelsonLabsEuropeScraper(WorkdayScraper):
    key = "nelson-labs-europe"
    label = "Nelson Labs Europe"
    host = "https://soterahealth.wd501.myworkdayjobs.com"
    tenant = "soterahealth"
    site = "External"
    search_text = "Belgium"
    location_tokens = frozenset({"leuven"})
    careers_url = "https://soterahealth.wd501.myworkdayjobs.com/External"
