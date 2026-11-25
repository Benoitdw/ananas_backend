"""Tri des offres de la « Liste An » pour un profil scientifique.

Pas de score ici: on ecarte seulement l'evident (technicien, informatique,
finance, vente, soins...) et on applique les consignes par employeur de la
liste (« uniquement labo ou recherche clinique » pour les hopitaux, etc.).
Rien n'est supprime: une offre ecartee garde sa raison, et l'onglet peut la
reafficher. En cas de doute, on garde.

Les regles raisonnent par *concepts*, jamais par chaine exacte: chaque concept
est une famille de radicaux FR/NL/EN, compares sur un texte normalise (sans
accents, minuscules, ponctuation ecrasee). « Technicien.ne », « technician »,
« technieker » et « Technicien(ne) » tombent tous dans le meme concept.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass


def normalize(text: str | None) -> str:
    """'Technicien.ne de Laboratoire – Hématologie' -> 'technicien ne de laboratoire hematologie'."""
    if not text:
        return ""
    ascii_only = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return " " + re.sub(r"[^a-z0-9%]+", " ", ascii_only.lower()).strip() + " "


class Concept:
    """Un ensemble de motifs equivalents. Chaque motif est une regex appliquee
    au texte normalise; ``\\b`` y marque un debut ou une fin de mot."""

    def __init__(self, *patterns: str):
        self.regex = re.compile("|".join(f"(?:{p})" for p in patterns))

    def found_in(self, *texts: str | None) -> bool:
        return any(self.regex.search(normalize(t)) for t in texts if t)


# ------------------------------------------------------------------ concepts

TECHNICIAN = Concept(
    r"\btechnic(ien|ian|ienne)s?\b", r"\btechnieker", r"\btechnisch (medewerker|inspecteur)",
    r"\boperat(eur|or|rice|rices)s?\b", r"\bouvri(er|ere)", r"\bmagasin", r"\bmagazijn",
    r"\bwarehouse", r"\bchauffeur", r"\bdriver\b", r"\bcontrema[i]?tre", r"\bsurveillant",
    r"\bmaintenance\b", r"\bonderhoud", r"\bentretien\b", r"\blingerie", r"\bnettoyage",
    r"\bschoonmaak", r"\bstaalnemer", r"\bechantillonneur", r"\bintendan(t|ce)",
)
IT = Concept(
    r"\bit\b", r"\bict\b", r"\bitot\b", r"\binformati(que|cien|ca)", r"\bdevelop(er|peur)",
    r"\bdeveloppeu", r"\bsoftware\b", r"\bprogramm(er|eur)", r"\bcyber", r"\bnetwork security",
    r"\barchitecte? (reseau|network|solution|logiciel)", r"\bsolution architect",
    r"\bsystem engineer", r"\bot system", r"\bautomation engineer", r"\bservice desk",
    r"\bhelpdesk", r"\bhelp desk", r"\bapplication (analyst|specialist|manager)",
    r"\bmicrosoft\b", r"\bdata platform", r"\bdevops", r"\bsap\b", r"\bpower bi",
    r"\bcognos", r"\bdigital (solution|technology)", r"\binfrastructure it",
)
ADMIN_FINANCE = Concept(
    r"\bcomptab", r"\baccount(ant|ing)\b", r"\bboekhoud", r"\bcontroller\b", r"\bcontroleur de gestion",
    r"\bfinanc(e|ier|iere|ial)\b", r"\btreasury", r"\btresorerie", r"\bpayroll", r"\bpaie\b",
    r"\bsecretai?re", r"\bsecretary", r"\bmanagement assistant", r"\bassistant e? administrati",
    r"\bassistante? de direction", r"\badministratie?f", r"\bagent d accueil", r"\breception",
    r"\bbusiness administration", r"\bcall ?center", r"\bjuridique", r"\blegal\b", r"\bjurist", r"\bgestionnaire legs",
    r"\bmarches publics", r"\bopenbare aanbesteding", r"\bpatrimoine", r"\bimmobili",
    r"\breal estate", r"\bfacilit(y|ies|eit)", r"\bcustoms\b", r"\bdouane",
)
HR = Concept(
    r"\bhr\b", r"\brh\b", r"\bressources humaines", r"\bhuman resources", r"\btalent (acquisition|partner|management)",
    # Pas « recrutement »: « Recrutement interne », « Reserve de recrutement »
    # figurent dans des titres de postes scientifiques.
    r"\brecruiter", r"\brecruitment (partner|specialist|officer)", r"\brecrut(eur|euse)",
    r"\bcompensation (and )?benefits",
    r"\bde i\b", r"\bdiversity",
)
SALES_MARKETING = Concept(
    r"\bsales\b", r"\bvente", r"\bverkoo?p", r"\bcommerci", r"\baccount manager",
    r"\bkey account", r"\bbusiness development", r"\bmarketing", r"\bcustomer (service|support|care)",
    r"\bservice client", r"\bklantendienst", r"\bproduct specialist", r"\bmarket access",
    r"\bactivation manager",
)
PROCUREMENT_LOGISTICS = Concept(
    r"\bachat", r"\bacheteu", r"\bbuyer\b", r"\bprocurement", r"\bpurchas", r"\baankop(er|en)",
    r"\binkoop", r"\bsupply chain", r"\blogisti", r"\bimport (and )?export", r"\bdistribution planning",
    r"\bcold chain",
)
CARE = Concept(
    r"\binfirmi(er|ere)s?\b", r"\bnurse", r"\bverpleeg", r"\baide soignant", r"\bzorgkundige",
    r"\bkinesi", r"\bkine\b", r"\bphysiotherap", r"\bergotherap", r"\blogoped", r"\bdietetici",
    r"\bsage femme", r"\bvroedvrouw", r"\bdentist", r"\bpsychologue", r"\bpsycholoog",
    r"\baccompagnat", r"\beducat(eur|rice)", r"\bjobiste", r"\bambulanc",
)
ENGINEERING_SITE = Concept(
    r"\belectric(ite|ity|al|ien)", r"\belektric", r"\bhoogspanning", r"\bthermique",
    r"\butilities\b", r"\bcad\b", r"\bsecurity (and )?crisis", r"\bprevention\b",
    r"\bconseiller e? en prevention", r"\bpreventieadviseur", r"\bveiligheidscoordinator",
    r"\bcouture",
)

# Doctorats (demande du 2026-11-25: le profil vise postdoc et au-dela). Le
# « post » devant est exclu: « Post-doctoral », « post-PhD » restent.
PHD = Concept(
    r"(?<!post )\bph ?d\b", r"(?<!post )\bdoctora(l|t|nt|at)", r"\bdoctorand",
)

# Exclusion generale: (concept, raison affichee). Premier qui matche gagne.
GENERAL_EXCLUSIONS: list[tuple[Concept, str]] = [
    (PHD, "doctorat (PhD)"),
    (TECHNICIAN, "technique / maintenance"),
    (IT, "informatique"),
    (HR, "RH"),
    (SALES_MARKETING, "commercial / marketing"),
    (PROCUREMENT_LOGISTICS, "achats / logistique"),
    (ADMIN_FINANCE, "administratif / finance"),
    (CARE, "soins / paramedical"),
    (ENGINEERING_SITE, "technique / maintenance"),
]

LAB_OR_CLINICAL_RESEARCH = Concept(
    r"\blabo", r"\blaborat", r"\blaborant", r"\bbiolog", r"\bpatholog", r"\bgenet",
    r"\bmicrobio", r"\bbiochim", r"\bbiochem", r"\bhemato", r"\bimmuno", r"\bcytolog",
    r"\bhistolog", r"\bbiobank", r"\bbiobanque",
    r"\brecherche", r"\bresearch", r"\bonderzoek", r"\bclinical (trial|stud|research|data)",
    r"\b(essai|etude)s? cliniques?", r"\bklinisch onderzoek", r"\bstudy (coordinator|nurse|manager)",
    r"\bcoordinat(eur|rice|or) d etudes?", r"\bdata manag", r"\bscienti", r"\bwetenschap",
)

# Mode de travail. On n'ecarte que sur une mention explicite de travail
# entierement sur site; une offre muette passe.
FLEXIBLE_WORK = Concept(
    r"\bhybri", r"\bremote", r"\bteletravail", r"\btele travail", r"\bthuiswerk",
    r"\bwork(ing)? from home", r"\bhome ?office", r"\bwfh\b", r"\bflexible (work|schedule|working)",
    r"\b\d+ (days?|jours?|dagen) (from|at|of|de|van)? ?(home|remote|teletravail|thuis)",
)
ON_SITE_ONLY = Concept(
    r"\b100 ?% (on ?site|onsite|sur site|op locatie|presentiel|in office)",
    r"\bfully (on ?site|onsite|office based)", r"\b(on ?site|onsite) only\b",
    r"\bsur site uniquement", r"\buniquement sur site", r"\bentierement sur site",
    r"\bno (remote|home ?working|teleworking)",
)


# ------------------------------------------------------------ regles par site


@dataclass(frozen=True)
class Offer:
    title: str
    location: str | None = None
    department: str | None = None
    description: str | None = None


Rule = Callable[[Offer], str | None]


def only_lab_or_clinical_research(offer: Offer) -> str | None:
    """Hopitaux: « uniquement labo ou recherche clinique »."""
    if LAB_OR_CLINICAL_RESEARCH.found_in(offer.title, offer.department):
        return None
    return "hopital: hors labo / recherche clinique"


GSK_DEPARTMENTS = Concept(
    r"\bmanufactur", r"\bmedical", r"\bclinical", r"\bquality", r"\bscience",
)


def gsk_departments(offer: Offer) -> str | None:
    """GSK: Manufacturing, Medical and Clinical, Quality, Science and
    Technology, MS&T. Departement inconnu: on garde."""
    if not offer.department or GSK_DEPARTMENTS.found_in(offer.department):
        return None
    return f"GSK: departement {offer.department}"


def sgs_laboratory(offer: Offer) -> str | None:
    """SGS: categorie « Laboratory and Testing » uniquement."""
    if not offer.department or Concept(r"\blaborat", r"\blabo\b").found_in(offer.department):
        return None
    return f"SGS: categorie {offer.department}"


EUROFINS_PLACES = Concept(r"\brixensart", r"\bbrussel", r"\bbruxelles", r"\bwavre", r"\bwaver\b")


def eurofins_places(offer: Offer) -> str | None:
    """Eurofins: uniquement Rixensart, Bruxelles et Wavre. Lieu inconnu: on garde."""
    if not offer.location or EUROFINS_PLACES.found_in(offer.location):
        return None
    return f"Eurofins: lieu {offer.location}"


def hybrid_if_stated(offer: Offer) -> str | None:
    """CellCarta (Anvers): « si hybrid ». Ecartee seulement si l'offre dit
    clairement que tout se passe sur site."""
    texts = (offer.title, offer.description)
    if FLEXIBLE_WORK.found_in(*texts) or not ON_SITE_ONLY.found_in(*texts):
        return None
    return "CellCarta: entierement sur site"


HOSPITALS = (
    "cliniques-universitaires-saint-luc",
    "hopitaux-iris-sud",
    "clinique-saint-pierre-ottignies",
    "chu-helora",
    "chu-ucl-namur",
)

COMPANY_RULES: dict[str, Rule] = {
    **{slug: only_lab_or_clinical_research for slug in HOSPITALS},
    "gsk-wavre": gsk_departments,
    "gsk-rixensart": gsk_departments,
    "sgs-lab-simon": sgs_laboratory,
    "eurofins-belgium": eurofins_places,
    "cellcarta": hybrid_if_stated,
}


def exclusion_reason(company_slug: str, offer: Offer) -> str | None:
    """Pourquoi l'offre est ecartee, ou None si elle reste.

    La consigne de l'employeur passe d'abord (c'est la plus parlante), puis
    le filtre general, sur le titre seulement: une description cite toujours
    l'informatique ou la logistique quelque part.
    """
    rule = COMPANY_RULES.get(company_slug)
    if rule and (reason := rule(offer)):
        return reason
    for concept, reason in GENERAL_EXCLUSIONS:
        if concept.found_in(offer.title):
            return reason
    return None
