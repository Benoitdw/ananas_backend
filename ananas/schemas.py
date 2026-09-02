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
    city: str
    lat: float | None
    lon: float | None
    geo_precision: str
    is_saved: bool = False
    has_scraper: bool = False
    open_jobs: int = 0


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
