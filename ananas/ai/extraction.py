"""Extraction de caracteristiques structurees, la seule etape qui appelle un LLM.

Deux extractions, deliberement separees:

- **L'offre**, une fois pour toutes et pour tout le monde. Une offre ne change
  pas d'un utilisateur a l'autre: la structurer N fois serait N-1 appels
  gaspilles. Le resultat est stocke sur l'offre.
- **Le profil**, une fois par enregistrement du CV.

Les deux produisent le *meme vocabulaire* (memes echelles de seniorite, memes
listes de competences en minuscules), ce qui rend la comparaison possible en
Python pur — voir ``ananas.ai.matching``. C'est ce decoupage qui evite un cout
en N_utilisateurs x N_offres, et qui fait qu'un modele local n'aurait a
remplacer que cette etape-ci.

``build_job_request`` assemble le triplet (system, prompt, schema) d'une offre
sans appeler le modele, et ``finalize_job_data`` nettoie une reponse brute:
c'est ce qui permet a l'extraction des offres de partir soit en appel direct
(``extract_job``), soit en lot (``ananas.ai.service.submit_extraction_batch``)
sans dupliquer le prompt ni le nettoyage. Le profil, lui, reste toujours en
appel direct: l'utilisateur attend son resultat a l'ecran.
"""

from __future__ import annotations

import logging

from ananas.ai.base import BatchItem, LLMError
from ananas.ai.registry import get_provider

log = logging.getLogger(__name__)

# Echelles partagees par les deux extractions. Toute valeur hors liste est
# rejetee par la generation contrainte, ce qui garantit que la comparaison
# n'aura pas a gerer de synonymes.
SENIORITY = ["stage", "junior", "confirme", "senior", "lead", "direction", "inconnu"]
CONTRACT = ["cdi", "cdd", "stage", "freelance", "interim", "alternance", "inconnu"]
REMOTE = ["sur_site", "hybride", "distanciel", "inconnu"]

_LIST = {"type": "array", "items": {"type": "string"}}

JOB_SCHEMA = {
    "type": "object",
    "properties": {
        "role_family": {"type": "string"},
        "seniority": {"type": "string", "enum": SENIORITY},
        "years_experience_min": {"type": "integer"},
        "contract": {"type": "string", "enum": CONTRACT},
        "remote": {"type": "string", "enum": REMOTE},
        "skills": _LIST,
        "nice_to_have": _LIST,
        "domains": _LIST,
        "languages": _LIST,
        "locations": _LIST,
        "summary": {"type": "string"},
    },
    "required": [
        "role_family", "seniority", "years_experience_min", "contract",
        "remote", "skills", "nice_to_have", "domains", "languages",
        "locations", "summary",
    ],
}

PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "role_families": _LIST,
        "seniority": {"type": "string", "enum": SENIORITY},
        "years_experience": {"type": "integer"},
        "skills": _LIST,
        "domains": _LIST,
        "languages": _LIST,
        "locations": _LIST,
        "contracts": {"type": "array", "items": {"type": "string", "enum": CONTRACT}},
        "remote": {"type": "string", "enum": REMOTE},
        "avoid": _LIST,
        "summary": {"type": "string"},
    },
    "required": [
        "role_families", "seniority", "years_experience", "skills", "domains",
        "languages", "locations", "contracts", "remote", "avoid", "summary",
    ],
}

# Consignes communes: c'est la normalisation qui rend deux extractions
# comparables. Sans elle, "Python" et "programmation python" ne se
# rencontreraient jamais.
_COMMON = """Normalise systematiquement:
- competences et domaines en MINUSCULES, au singulier, sans article
  ("python", "affaires reglementaires", "gmp", "gestion de projet");
- une competence par entree, jamais de phrase;
- langues en code ISO 639-1 minuscule ("fr", "en", "nl");
- lieux sous la forme "Ville, Pays" ou "Pays" si la ville est absente.
N'invente rien: ce qui n'est pas dit vaut "inconnu", 0, ou une liste vide."""

JOB_SYSTEM = f"""Tu extrais les caracteristiques factuelles d'une offre d'emploi.

{_COMMON}

- `role_family`: la famille de metier en minuscules ("affaires reglementaires",
  "ingenierie donnees", "assurance qualite"), pas l'intitule exact du poste.
- `skills`: uniquement les competences exigees. `nice_to_have`: les souhaitees.
- `years_experience_min`: 0 si l'offre n'exige pas d'anciennete chiffree.
- `summary`: deux phrases maximum, en francais, factuelles."""

PROFILE_SYSTEM = f"""Tu extrais le profil professionnel d'une personne a partir de
son CV et de ce qu'elle recherche.

{_COMMON}

- `role_families`: les familles de metier VISEES, pas seulement celles deja
  exercees. Les aspirations priment sur l'historique.
- `skills`: ce que la personne maitrise, d'apres le CV.
- `avoid`: ce qu'elle dit explicitement ne pas vouloir. Liste vide sinon.
- `seniority` et `years_experience`: son niveau actuel.
- `summary`: deux phrases maximum, en francais."""


def normalize_terms(values: list[str]) -> list[str]:
    """Minuscules, sans doublon, ordre conserve.

    Filet de securite cote modele — il respecte la consigne la plupart du
    temps, pas toujours — et **regle de vocabulaire partagee**: les corrections
    manuelles du profil (``PATCH /api/me/profile/data``) passent par ici aussi.
    Une competence saisie "Western Blot" a la main doit devenir le meme
    "western blot" que celui extrait d'une offre, sans quoi les deux ne se
    rencontreraient jamais dans ``ananas.ai.matching``.
    """
    return list(dict.fromkeys(v.strip().lower() for v in values if v and v.strip()))


def build_job_request(
    *, title: str, company: str, location: str, department: str, description: str
) -> BatchItem:
    """Le triplet (system, prompt, schema) d'une offre, sans appeler le modele.

    Separe de ``extract_job`` pour servir aussi bien l'appel synchrone que la
    soumission par lot (``ananas.ai.service.submit_extraction_batch``): les
    deux chemins doivent construire exactement la meme requete.
    """
    prompt = "\n".join(
        [
            f"Entreprise: {company}",
            f"Intitule: {title}",
            f"Service: {department or 'non precise'}",
            f"Lieu(x): {location or 'non precise'}",
            "",
            "Annonce:",
            (description or "").strip()[:12000] or "(aucune description publiee)",
        ]
    )
    return BatchItem(system=JOB_SYSTEM, prompt=prompt, schema=JOB_SCHEMA)


def finalize_job_data(data: dict) -> dict:
    """Normalise la reponse brute du modele: listes en minuscules dedoublonnees,
    role_family en minuscules. Meme traitement, que la reponse vienne d'un
    appel direct ou d'un lot recolte plus tard."""
    for key in ("skills", "nice_to_have", "domains", "languages", "locations"):
        data[key] = normalize_terms(data.get(key) or [])
    data["role_family"] = (data.get("role_family") or "").strip().lower()
    return data


def extract_job(*, title: str, company: str, location: str, department: str, description: str) -> dict:
    """Caracteristiques d'une offre, en temps reel. Leve LLMError si le
    modele echoue. Repli synchrone quand le fournisseur ne fait pas de lot —
    voir ``ananas.ai.service.extract_job_features``."""
    provider = get_provider()
    if provider is None:
        raise LLMError("Aucun fournisseur de modele configure")

    item = build_job_request(
        title=title, company=company, location=location, department=department,
        description=description,
    )
    data = provider.complete_json(system=item.system, prompt=item.prompt, schema=item.schema)
    return finalize_job_data(data)


def extract_profile(*, cv: str, aspirations: str) -> dict:
    provider = get_provider()
    if provider is None:
        raise LLMError("Aucun fournisseur de modele configure")

    prompt = "\n".join(
        [
            "CV:",
            (cv or "").strip()[:20000] or "(non fourni)",
            "",
            "Aspirations professionnelles:",
            (aspirations or "").strip()[:4000] or "(non precisees)",
        ]
    )
    data = provider.complete_json(system=PROFILE_SYSTEM, prompt=prompt, schema=PROFILE_SCHEMA)

    for key in ("role_families", "skills", "domains", "languages", "locations", "avoid"):
        data[key] = normalize_terms(data.get(key) or [])
    return data
