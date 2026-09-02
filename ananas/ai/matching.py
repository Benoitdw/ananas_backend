"""Correspondance entre un profil et une offre. **Aucun appel au modele ici.**

Les deux cotes ont ete ramenes au meme vocabulaire par l'extraction, ce qui
rend la comparaison calculable en Python. C'est un choix de conception, pas une
economie de moyens:

- **cout**: comparer par LLM couterait N_utilisateurs x N_offres appels, a
  refaire des qu'un profil change. Ici c'est gratuit, donc on peut scorer
  toutes les paires et filtrer les offres d'une entreprise a la demande;
- **explicabilite**: on peut dire *pourquoi* une offre matche, et l'interface
  l'affiche;
- **stabilite**: deux executions donnent le meme score, ce qu'un LLM ne
  garantit pas;
- **portabilite**: passer a un modele local ne touche que l'extraction.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Echelle de seniorite, ordonnee. 'inconnu' est traite a part.
LEVELS = {"stage": 0, "junior": 1, "confirme": 2, "senior": 3, "lead": 4, "direction": 5}

# Ponderations, somme = 100. Les competences et la famille de metier pesent le
# plus: c'est ce qui distingue reellement deux offres du meme secteur.
WEIGHTS = {
    "skills": 32,
    "role": 24,
    "seniority": 18,
    "domains": 12,
    "languages": 6,
    "location": 4,
    "remote": 4,
}

# Une offre explicitement rejetee par l'utilisateur ne doit pas remonter,
# meme si tout le reste correspond.
AVOID_PENALTY = 45


@dataclass
class MatchResult:
    score: int
    reasons: list[str] = field(default_factory=list)
    # Detail par critere, pour pouvoir expliquer ou deboguer un score
    parts: dict[str, int] = field(default_factory=dict)


def _tokens(term: str) -> set[str]:
    return {t for t in term.replace("-", " ").replace("/", " ").split() if len(t) > 2}


def similar(a: str, b: str) -> bool:
    """Deux termes designent-ils la meme chose ?

    Volontairement lexical: l'extraction ayant deja normalise (minuscules,
    singulier, sans article), il reste surtout des variantes de formulation
    ("gestion de projet" / "gestion projet"). Pas d'embeddings: ce serait une
    dependance de plus pour un gain marginal a ce stade.
    """
    a, b = a.strip(), b.strip()
    if not a or not b:
        return False
    if a == b:
        return True
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return False
    if ta <= tb or tb <= ta:  # l'un est contenu dans l'autre
        return True
    return len(ta & tb) / len(ta | tb) >= 0.6


def _overlap(wanted: list[str], owned: list[str]) -> list[str]:
    """Elements de `wanted` couverts par `owned`."""
    return [w for w in wanted if any(similar(w, o) for o in owned)]


def _ratio(matched: int, total: int) -> float:
    return matched / total if total else 0.0


def score_job(profile: dict, features: dict) -> MatchResult:
    """Score 0-100 et raisons lisibles."""
    parts: dict[str, int] = {}
    reasons: list[str] = []

    # --- competences exigees
    required = features.get("skills") or []
    owned = profile.get("skills") or []
    if required:
        hit = _overlap(required, owned)
        parts["skills"] = round(WEIGHTS["skills"] * _ratio(len(hit), len(required)))
        if hit:
            shown = ", ".join(hit[:4])
            reasons.append(f"{len(hit)}/{len(required)} competences requises : {shown}")
        else:
            reasons.append("aucune competence requise en commun")
    else:
        # Offre sans exigence explicite: on ne penalise pas, on n'attribue pas
        # non plus le maximum a l'aveugle.
        parts["skills"] = round(WEIGHTS["skills"] * 0.5)

    # --- famille de metier visee
    role = features.get("role_family") or ""
    targets = profile.get("role_families") or []
    if role and targets:
        matched = any(similar(role, t) for t in targets)
        parts["role"] = WEIGHTS["role"] if matched else 0
        reasons.append(
            f"metier vise : {role}" if matched else f"metier different de tes cibles : {role}"
        )
    else:
        parts["role"] = round(WEIGHTS["role"] * 0.5)

    # --- seniorite
    parts["seniority"], seniority_reason = _seniority(profile, features)
    if seniority_reason:
        reasons.append(seniority_reason)

    # --- secteurs
    domains = features.get("domains") or []
    mine = profile.get("domains") or []
    if domains and mine:
        hit = _overlap(domains, mine)
        parts["domains"] = round(WEIGHTS["domains"] * _ratio(len(hit), len(domains)))
        if hit:
            reasons.append(f"secteur : {', '.join(hit[:3])}")
    else:
        parts["domains"] = round(WEIGHTS["domains"] * 0.5)

    # --- langues: une langue exigee qu'on ne parle pas est bloquante en pratique
    needed = features.get("languages") or []
    spoken = profile.get("languages") or []
    if needed and spoken:
        missing = [lang for lang in needed if not any(similar(lang, s) for s in spoken)]
        parts["languages"] = round(WEIGHTS["languages"] * _ratio(len(needed) - len(missing), len(needed)))
        if missing:
            reasons.append(f"langue(s) exigee(s) non declaree(s) : {', '.join(missing)}")
    else:
        parts["languages"] = WEIGHTS["languages"]

    # --- lieu
    places = features.get("locations") or []
    wanted_places = profile.get("locations") or []
    if places and wanted_places:
        hit = _overlap(places, wanted_places)
        parts["location"] = WEIGHTS["location"] if hit else 0
        if not hit:
            reasons.append(f"lieu : {', '.join(places[:2])}")
    else:
        parts["location"] = round(WEIGHTS["location"] * 0.5)

    # --- teletravail
    parts["remote"] = _remote(profile.get("remote"), features.get("remote"))

    total = sum(parts.values())

    # --- rejets explicites
    avoid = profile.get("avoid") or []
    haystack = [role, *(features.get("skills") or []), *domains, features.get("summary", "").lower()]
    if avoid and (blocked := [a for a in avoid if any(similar(a, h) for h in haystack if h)]):
        total -= AVOID_PENALTY
        reasons.insert(0, f"contient ce que tu veux eviter : {', '.join(blocked[:2])}")

    return MatchResult(score=max(0, min(100, round(total))), reasons=reasons, parts=parts)


def _seniority(profile: dict, features: dict) -> tuple[int, str]:
    """Un poste au-dessus du niveau reste interessant; deux crans en dessous,
    beaucoup moins. L'ecart est donc asymetrique."""
    weight = WEIGHTS["seniority"]
    job_level = LEVELS.get(features.get("seniority", "inconnu"))
    my_level = LEVELS.get(profile.get("seniority", "inconnu"))

    if job_level is None or my_level is None:
        base = round(weight * 0.5)
    else:
        gap = job_level - my_level
        if gap <= -2:
            base = round(weight * 0.35)  # nettement sous-qualifie pour la personne
        elif gap == -1:
            base = round(weight * 0.8)
        elif gap == 0:
            base = weight
        elif gap == 1:
            base = round(weight * 0.7)  # un cran au-dessus: atteignable
        else:
            base = round(weight * 0.2)

    required_years = features.get("years_experience_min") or 0
    my_years = profile.get("years_experience") or 0
    if required_years and my_years < required_years:
        missing = required_years - my_years
        # 15% du poids retire par annee manquante, plafonne
        base = round(base * max(0.3, 1 - 0.15 * missing))
        return base, f"{required_years} ans demandes, tu en declares {my_years}"

    if job_level is not None and my_level is not None:
        return base, f"niveau {features['seniority']} pour un profil {profile['seniority']}"
    return base, ""


def _remote(preferred: str | None, offered: str | None) -> int:
    weight = WEIGHTS["remote"]
    if not preferred or not offered or "inconnu" in (preferred, offered):
        return round(weight * 0.5)
    if preferred == offered:
        return weight
    # Le distanciel satisfait qui veut de l'hybride, et inversement a moitie
    tolerant = {("hybride", "distanciel"), ("distanciel", "hybride"), ("hybride", "sur_site")}
    return round(weight * 0.5) if (preferred, offered) in tolerant else 0
