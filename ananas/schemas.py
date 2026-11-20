"""DTO Pydantic — le contrat HTTP entre l'API et le front (depot separe)."""

from __future__ import annotations

import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------- auth


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(ORM):
    id: int
    email: str
    created_at: datetime
    is_admin: bool = False


# -------------------------------------------------------------------- offres


class JobOut(ORM):
    id: int
    title: str
    url: str
    location: str | None
    department: str | None = None
    posted_at: date | None
    first_seen_at: datetime
    closed_at: datetime | None
    # Renseignes quand l'utilisateur a un profil et que l'offre est caracterisee
    match_score: int | None = None
    match_reasons: list[str] = []
    summary: str | None = None


class JobWithCompany(JobOut):
    company_id: int
    company_name: str
    company_slug: str
    # False quand l'offre vient d'une entreprise que l'utilisateur ne suit
    # pas encore (feed "toutes les entreprises", voir GET /api/me/jobs?scope=all)
    company_saved: bool = True
    # L'utilisateur a explicitement ecarte cette offre. Absente du feed par
    # defaut (voir include_hidden), presente quand on demande a les revoir.
    is_hidden: bool = False
    # Distance du siege de l'entreprise au domicile de l'utilisateur. C'est
    # une approximation assumee: `location` est un texte libre non geocode,
    # et une offre bruxelloise d'une societe basee a Gand sortira a Gand.
    distance_km: float | None = None


# ---------------------------------------------------------------- entreprises


class CompanyListItem(ORM):
    """Charge utile allegee: une seule requete peuple toute la carte."""

    id: int
    slug: str
    name: str
    type: str
    core_business: str
    tags: str = ""
    source: str = "biowin"
    # Categorie dans la Liste An; None = hors liste
    liste_an_category: str | None = None
    city: str
    lat: float | None
    lon: float | None
    geo_precision: str
    is_saved: bool = False
    # Masquee par l'utilisateur: absente de la carte et du feed par defaut,
    # renvoyee seulement quand on demande a la revoir (include_hidden).
    is_hidden: bool = False
    has_scraper: bool = False
    open_jobs: int = 0
    # Distance a vol d'oiseau depuis le domicile, en km. None quand
    # l'utilisateur n'a pas de domicile localise ou l'entreprise pas de
    # coordonnees — un tiret cote interface, jamais un zero invente.
    distance_km: float | None = None


class CompanyDetail(ORM):
    id: int
    slug: str
    name: str
    type: str
    core_business: str
    tags: str = ""
    source: str = "biowin"
    submitted_by_email: str | None = None
    other_tags: str
    baseline: str
    description: str
    street: str
    city: str
    postal_code: str
    country: str
    address: str
    lat: float | None
    lon: float | None
    geo_precision: str
    website: str
    email: str
    phone: str
    linkedin: str
    logo: str
    source_url: str
    careers_url: str | None
    scraper_key: str | None
    last_scraped_at: datetime | None
    is_saved: bool = False
    # La fiche reste consultable une fois masquee — c'est de la qu'on demasque.
    is_hidden: bool = False
    distance_km: float | None = None
    # L'administration, ou l'utilisateur qui a propose cette entreprise
    can_edit: bool = False
    jobs: list[JobOut] = []
    # Seuil de l'utilisateur, pour que le front puisse proposer
    # "offres pertinentes uniquement" sans second appel
    match_threshold: int | None = None


class CompanyFacets(BaseModel):
    """Valeurs distinctes pour alimenter les filtres de la sidebar.

    ``tags`` reunit les secteurs BioWin et les tags saisis par les
    utilisateurs: un seul vocabulaire, donc un seul filtre.
    """

    types: list[str]
    tags: list[str]
    # Conserve pour compatibilite: meme contenu que `tags`
    core_businesses: list[str]


# ------------------------------------------------ soumission d'une entreprise


MAX_TAGS = 8


def normalize_tag(raw: str) -> str:
    """Un tag propre, sinon la liste de facettes se remplit de quasi-doublons.

    'BIOTECH ', ' biotech' et 'Biotech' doivent produire la meme entree, sans
    quoi le filtre devient inutilisable pour les autres utilisateurs — ce qui
    est precisement le but des tags.
    """
    cleaned = re.sub(r"\s+", " ", raw).strip(" ,;·-").strip()
    if not cleaned:
        return ""
    # Capitalisation douce: on respecte les sigles deja en majuscules (IVD, CRO)
    words = [w if w.isupper() and len(w) <= 5 else w.capitalize() for w in cleaned.split(" ")]
    return " ".join(words)[:60]


class CompanySubmitIn(BaseModel):
    """Formulaire de proposition d'entreprise.

    Seul le nom est obligatoire: exiger une adresse complete decouragerait les
    contributions, et le geocodage sait degrader (ville seule, voire nom seul).
    """

    name: str = Field(min_length=2, max_length=255)
    tags: list[str] = Field(default_factory=list)

    website: str = ""
    careers_url: str = ""
    type: str = ""
    baseline: str = Field(default="", max_length=500)
    description: str = Field(default="", max_length=4000)

    street: str = ""
    postal_code: str = ""
    city: str = ""
    country: str = "Belgium"

    email: str = ""
    phone: str = ""
    linkedin: str = ""

    # Coche par defaut cote formulaire: on propose surtout une entreprise
    # qu'on veut soi-meme suivre.
    save: bool = True

    @field_validator("tags", mode="after")
    @classmethod
    def _clean_tags(cls, tags: list[str]) -> list[str]:
        seen: dict[str, None] = {}
        for tag in tags:
            if normalized := normalize_tag(tag):
                seen.setdefault(normalized, None)
        if len(seen) > MAX_TAGS:
            raise ValueError(f"{MAX_TAGS} tags au maximum")
        return list(seen)

    @field_validator("website", "careers_url", "linkedin", mode="after")
    @classmethod
    def _clean_url(cls, url: str) -> str:
        url = url.strip()
        if url and not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        return url[:500]

    @field_validator("name", "type", "street", "postal_code", "city", "country", "email", "phone")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class SubmitConflict(BaseModel):
    """Renvoye en 409 quand l'entreprise existe deja: le front propose alors
    d'ouvrir la fiche existante plutot que de creer un doublon."""

    detail: str
    company_id: int
    company_name: str


# -------------------------------------------------- edition d'une entreprise


class CompanyUpdateIn(BaseModel):
    """Champs modifiables d'une fiche, tous facultatifs (semantique PATCH).

    Un champ absent n'est pas touche — c'est ce qui permet a l'interface
    d'envoyer une correction de detail sans reposter toute la fiche, et de ne
    jamais ecraser par du vide ce qu'elle n'affiche pas.

    Volontairement absents: `source`, `slug`, `scraper_key` et les
    coordonnees. Les deux premiers sont des identites, le troisieme se branche
    par le nom du fichier de scraper (voir seed.py), et les coordonnees sont
    recalculees par le serveur quand l'adresse change.
    """

    name: str | None = Field(default=None, min_length=2, max_length=255)
    tags: list[str] | None = None

    website: str | None = None
    careers_url: str | None = None
    type: str | None = None
    baseline: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=4000)

    street: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country: str | None = None

    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None

    @field_validator("tags", mode="after")
    @classmethod
    def _clean_tags(cls, tags: list[str] | None) -> list[str] | None:
        if tags is None:
            return None
        seen: dict[str, None] = {}
        for tag in tags:
            if normalized := normalize_tag(tag):
                seen.setdefault(normalized, None)
        if len(seen) > MAX_TAGS:
            raise ValueError(f"{MAX_TAGS} tags au maximum")
        return list(seen)

    @field_validator("website", "careers_url", "linkedin", mode="after")
    @classmethod
    def _clean_url(cls, url: str | None) -> str | None:
        if url is None:
            return None
        url = url.strip()
        if url and not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        return url[:500]

    @field_validator("name", "type", "street", "postal_code", "city", "country", "email", "phone")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


# ------------------------------------------------- domicile et perimetre


MAX_RADIUS_KM = 500


class HomeIn(BaseModel):
    """Domicile de reference. Aucun champ n'est obligatoire: une ville seule
    suffit a placer un cercle utile, et exiger une rue empecherait quelqu'un
    de simplement dire "je cherche autour de Namur"."""

    street: str = ""
    postal_code: str = ""
    city: str = ""
    country: str = "Belgium"
    radius_km: int = Field(default=25, ge=1, le=MAX_RADIUS_KM)
    # Appliquer ce rayon a la notification quotidienne, et pas seulement aux
    # filtres de l'interface.
    notify_within_radius: bool = False

    @field_validator("street", "postal_code", "city", "country")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class HomeOut(ORM):
    """L'adresse telle qu'enregistree, plus ce que le geocodage en a fait.

    ``lat``/``lon`` alimentent le cercle trace sur la carte et le calcul des
    distances; ``geo_precision`` permet a l'interface de dire honnetement que
    le point n'est qu'approximatif.
    """

    street: str = ""
    postal_code: str = ""
    city: str = ""
    country: str = "Belgium"
    address: str = ""
    lat: float | None = None
    lon: float | None = None
    geo_precision: str = ""
    radius_km: int = 25
    notify_within_radius: bool = False
    updated_at: datetime | None = None


# ------------------------------------------------------------ administration


class AdminUserOut(ORM):
    """Une ligne du tableau des comptes.

    Les compteurs disent l'essentiel de ce qu'un compte fait de l'outil —
    entreprises suivies, canal de notification configure, profil analyse —
    sans donner acces a son contenu: ni CV, ni aspirations, ni chat_id.
    """

    id: int
    email: str
    created_at: datetime
    is_active: bool
    is_admin: bool
    saved_companies: int = 0
    submitted_companies: int = 0
    channels: int = 0
    has_profile: bool = False


class AdminStatsOut(BaseModel):
    users: int
    companies: int
    companies_by_source: dict[str, int]
    user_submissions: int
    jobs_open: int
    scrapers: int


# ------------------------------------------------------------------- canaux


class ChannelIn(BaseModel):
    type: str = "telegram"
    target: str = Field(min_length=1, max_length=255)
    enabled: bool = True


class ChannelUpdate(BaseModel):
    target: str | None = Field(default=None, min_length=1, max_length=255)
    enabled: bool | None = None


class ChannelOut(ORM):
    id: int
    type: str
    target: str
    enabled: bool
    created_at: datetime
    last_sent_at: datetime | None


class TelegramLinkOut(BaseModel):
    """Liaison ouverte: de quoi afficher le bouton, le QR et le code de repli."""

    code: str
    url: str
    bot_username: str
    expires_at: datetime


class TelegramLinkStatus(BaseModel):
    status: str  # 'pending' | 'linked'
    channel: ChannelOut | None = None


# ---------------------------------------------- profil et correspondance


class ProfileIn(BaseModel):
    cv_text: str = Field(default="", max_length=40000)
    aspirations: str = Field(default="", max_length=4000)


class ProfilePreferencesIn(BaseModel):
    match_threshold: int | None = Field(default=None, ge=0, le=100)
    notify_only_relevant: bool | None = None


# Nombre d'entrees par liste. Genereux — un CV riche depasse facilement
# vingt competences — mais borne: la charge utile est rejouee a chaque
# scoring, et une liste de mille termes ralentirait tout le monde.
MAX_PROFILE_TERMS = 80
MAX_TERM_LENGTH = 80


class ProfileDataIn(BaseModel):
    """Correction manuelle du profil structure, champ par champ (PATCH).

    Ce que le modele a compris n'est pas toujours juste, et reecrire son CV
    pour faire disparaitre une competence mal lue est un detour absurde. Cette
    route corrige directement le resultat — celui qui sert au calcul des
    scores.

    Deux contraintes tiennent la coherence du systeme:

      - les termes libres repassent par ``normalize_terms``, la meme fonction
        que l'extraction: une competence corrigee a la main doit atterrir dans
        le vocabulaire exact des offres, sinon elle ne matchera jamais;
      - ``seniority``, ``remote`` et ``contracts`` restent bornes aux echelles
        partagees, que ``ananas.ai.matching`` sait comparer.

    Un champ absent n'est pas touche. ``contracts`` est accepte par souci de
    fidelite au profil extrait, mais n'entre pas dans le score aujourd'hui.
    """

    role_families: list[str] | None = None
    seniority: str | None = None
    years_experience: int | None = Field(default=None, ge=0, le=60)
    skills: list[str] | None = None
    domains: list[str] | None = None
    languages: list[str] | None = None
    locations: list[str] | None = None
    contracts: list[str] | None = None
    remote: str | None = None
    avoid: list[str] | None = None

    @field_validator(
        "role_families", "skills", "domains", "languages", "locations", "avoid", mode="after"
    )
    @classmethod
    def _clean_terms(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        from ananas.ai.extraction import normalize_terms

        cleaned = normalize_terms([v[:MAX_TERM_LENGTH] for v in values])
        if len(cleaned) > MAX_PROFILE_TERMS:
            raise ValueError(f"{MAX_PROFILE_TERMS} entrees au maximum par champ")
        return cleaned

    @field_validator("seniority", mode="after")
    @classmethod
    def _check_seniority(cls, value: str | None) -> str | None:
        from ananas.ai.extraction import SENIORITY

        return _one_of(value, SENIORITY, "niveau")

    @field_validator("remote", mode="after")
    @classmethod
    def _check_remote(cls, value: str | None) -> str | None:
        from ananas.ai.extraction import REMOTE

        return _one_of(value, REMOTE, "mode de travail")

    @field_validator("contracts", mode="after")
    @classmethod
    def _check_contracts(cls, values: list[str] | None) -> list[str] | None:
        from ananas.ai.extraction import CONTRACT

        if values is None:
            return None
        return list(dict.fromkeys(_one_of(v, CONTRACT, "contrat") for v in values))


def _one_of(value: str | None, allowed: list[str], label: str) -> str | None:
    """Borne une valeur a une echelle partagee avec l'extraction.

    Refuser plutot que corriger en silence: une valeur hors echelle ne peut
    venir que d'un client qui ne parle pas le meme vocabulaire, et l'accepter
    donnerait un profil que le scoring ignorerait sans rien dire.
    """
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in allowed:
        raise ValueError(f"{label} inconnu: {value!r} (attendu: {', '.join(allowed)})")
    return normalized


class CvImportOut(BaseModel):
    """Texte extrait d'un PDF, avant enregistrement."""

    text: str
    pages: int
    filename: str
    # 'texte' = couche texte du PDF, 'modele' = PDF scanne transcrit par le modele
    method: str


class ProfileOut(ORM):
    cv_text: str
    aspirations: str
    match_threshold: int
    notify_only_relevant: bool
    status: str | None
    error: str | None
    extracted_at: datetime | None
    version: int
    # Forme structuree, affichee pour que l'utilisateur voie ce qui a ete
    # compris de son CV — et puisse le corriger si c'est faux.
    data: dict | None = None
    ai_available: bool = True


class MessageOut(BaseModel):
    detail: str
