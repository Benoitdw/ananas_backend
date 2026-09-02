"""DTO Pydantic — le contrat HTTP entre l'API et le front (depot separe)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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


# -------------------------------------------------------------------- offres


class JobOut(ORM):
    id: int
    title: str
    url: str
    location: str | None
    posted_at: date | None
    first_seen_at: datetime
    closed_at: datetime | None


class JobWithCompany(JobOut):
    company_id: int
    company_name: str
    company_slug: str


# ---------------------------------------------------------------- entreprises


class CompanyListItem(ORM):
    """Charge utile allegee: une seule requete peuple toute la carte."""

    id: int
    slug: str
    name: str
    type: str
    core_business: str
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
    jobs: list[JobOut] = []


class CompanyFacets(BaseModel):
    """Valeurs distinctes pour alimenter les filtres de la sidebar."""

    types: list[str]
    core_businesses: list[str]


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


class MessageOut(BaseModel):
    detail: str
