"""Modeles SQLAlchemy partages par l'API et le worker.

Deux contraintes portent toute la logique metier:

  - ``jobs.uq_job_company_fingerprint`` definit ce qu'est "la meme offre",
    et donc par difference ce qu'est une offre *nouvelle*.
  - ``sent_job_notifications`` (PK composite) garantit qu'une offre n'est
    jamais notifiee deux fois au meme utilisateur, meme si le worker est
    relance a la main ou plante en plein envoi.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ananas.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Toujours stocke en minuscules (voir ananas.security.normalize_email)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    # Un compte d'administration se cree par `python -m ananas.admin`, jamais
    # par l'inscription publique: aucune route ne peut lever ce drapeau.
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    channels: Mapped[list[NotificationChannel]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    saved: Mapped[list[SavedCompany]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class NotificationChannel(Base):
    """Un moyen de joindre un utilisateur.

    Table separee plutot que des colonnes sur ``users``: c'est ce qui permet
    d'ajouter un transport (email, Discord, webhook) sans migration du modele
    utilisateur, et a un utilisateur d'en cumuler plusieurs.
    """

    __tablename__ = "notification_channels"
    __table_args__ = (
        # Un seul canal par type et par utilisateur, pour eviter les doublons d'envoi
        UniqueConstraint("user_id", "type", name="uq_channel_user_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # Cle d'un notifier enregistre dans ananas.notifiers.registry ('telegram')
    type: Mapped[str] = mapped_column(String(32), default="telegram")
    # Adresse au sens du transport: chat_id Telegram, adresse mail, URL de webhook...
    target: Mapped[str] = mapped_column(String(255))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="channels")


# Provenance d'une entreprise. 'biowin' = importee du repertoire du POC,
# 'curated' = ajoutee au repertoire Ananas par un CSV de data/,
# 'from_user' = proposee par un utilisateur via le formulaire.
SOURCE_BIOWIN = "biowin"
SOURCE_CURATED = "curated"
SOURCE_USER = "from_user"


class Company(Base):
    """Une entreprise du repertoire, affichee sur la carte.

    Trois provenances (colonne ``source``): les 81 partenaires importes du CSV
    BioWin, les entreprises du repertoire Ananas (autres CSV de ``data/``), et
    celles proposees par les utilisateurs. Le reste du modele est identique —
    une entreprise proposee est une entreprise a part entiere, visible et
    enregistrable par tous.

    Les colonnes ``careers_url`` / ``scraper_key`` branchent une entreprise sur
    un scraper concret.
    """

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)

    # --- provenance
    source: Mapped[str] = mapped_column(
        String(16), default=SOURCE_BIOWIN, server_default=SOURCE_BIOWIN, index=True
    )
    submitted_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # --- classification
    type: Mapped[str] = mapped_column(String(120), default="")
    # Secteurs issus de BioWin. Vide pour une entreprise proposee.
    core_business: Mapped[str] = mapped_column(Text, default="")
    # Tags saisis par l'utilisateur qui propose l'entreprise, separes par des
    # virgules. Meme espace de noms que core_business: le filtre et la liste
    # de facettes interrogent les deux, pour qu'il n'y ait qu'un seul
    # vocabulaire de tags visible par tous.
    tags: Mapped[str] = mapped_column(Text, default="", server_default="")
    other_tags: Mapped[str] = mapped_column(Text, default="")
    baseline: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")

    # --- localisation
    street: Mapped[str] = mapped_column(String(255), default="")
    city: Mapped[str] = mapped_column(String(120), default="")
    postal_code: Mapped[str] = mapped_column(String(16), default="")
    country: Mapped[str] = mapped_column(String(80), default="")
    address: Mapped[str] = mapped_column(String(500), default="")
    # Nullable: 5 des 81 partenaires importes n'ont aucune adresse publiee
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 'adresse' | 'ville' | 'approx. (nom)' | 'non localise' — affiche a l'utilisateur
    # quand la position n'est pas exacte
    geo_precision: Mapped[str] = mapped_column(String(32), default="")

    # --- contact
    website: Mapped[str] = mapped_column(String(500), default="")
    email: Mapped[str] = mapped_column(String(320), default="")
    phone: Mapped[str] = mapped_column(String(64), default="")
    linkedin: Mapped[str] = mapped_column(String(500), default="")
    logo: Mapped[str] = mapped_column(String(1000), default="")
    source_url: Mapped[str] = mapped_column(String(500), default="", index=True)

    # --- scraping
    careers_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Doit correspondre a un BaseScraper.key enregistre. NULL = pas encore scrapee.
    scraper_key: Mapped[str | None] = mapped_column(String(80), nullable=True, unique=True)
    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_scrape_status: Mapped[str | None] = mapped_column(String(16), nullable=True)  # ok | error
    last_scrape_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    jobs: Mapped[list[Job]] = relationship(back_populates="company", cascade="all, delete-orphan")
    submitted_by: Mapped[User | None] = relationship()

    @property
    def all_tags(self) -> list[str]:
        """Tags BioWin et tags utilisateur reunis, dedoublonnes, dans l'ordre."""
        raw = f"{self.core_business},{self.tags}"
        return list(dict.fromkeys(t.strip() for t in raw.split(",") if t.strip()))


class SavedCompany(Base):
    """Une entreprise mise en favori par un utilisateur — ce qui declenche sa veille."""

    __tablename__ = "saved_companies"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True
    )
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="saved")
    company: Mapped[Company] = relationship()


class Job(Base):
    """Une offre d'emploi vue au moins une fois chez une entreprise.

    Les lignes ne sont jamais supprimees: une offre disparue du site recoit un
    ``closed_at``. C'est ce qui permet de distinguer "nouvelle offre" (insert)
    de "offre toujours la" (update de last_seen_at).
    """

    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("company_id", "fingerprint", name="uq_job_company_fingerprint"),
        Index("ix_jobs_first_seen_at", "first_seen_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    # sha256 calcule par JobPosting.fingerprint
    fingerprint: Mapped[str] = mapped_column(String(64))

    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(1000))
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    department: Mapped[str | None] = mapped_column(String(160), nullable=True)
    posted_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # NULL tant que l'offre est visible sur le site de l'entreprise
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    company: Mapped[Company] = relationship(back_populates="jobs")
    features: Mapped[JobFeatures | None] = relationship(
        back_populates="job", cascade="all, delete-orphan", uselist=False
    )

    @property
    def is_open(self) -> bool:
        return self.closed_at is None


class JobFeatures(Base):
    """Caracteristiques structurees d'une offre, extraites une seule fois.

    Une offre ne change pas d'un utilisateur a l'autre: la structurer par
    utilisateur serait N-1 appels de modele gaspilles. Ces caracteristiques
    sont donc communes, et la comparaison au profil se fait ensuite en Python
    (``ananas.ai.matching``).
    """

    __tablename__ = "job_features"

    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True
    )
    role_family: Mapped[str] = mapped_column(String(120), default="")
    seniority: Mapped[str] = mapped_column(String(16), default="inconnu")
    years_experience_min: Mapped[int] = mapped_column(Integer, default=0)
    contract: Mapped[str] = mapped_column(String(16), default="inconnu")
    remote: Mapped[str] = mapped_column(String(16), default="inconnu")
    # Listes de termes normalises, dans le meme vocabulaire que le profil
    skills: Mapped[list] = mapped_column(JSON, default=list)
    nice_to_have: Mapped[list] = mapped_column(JSON, default=list)
    domains: Mapped[list] = mapped_column(JSON, default=list)
    languages: Mapped[list] = mapped_column(JSON, default=list)
    locations: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text, default="")

    model: Mapped[str] = mapped_column(String(80), default="")
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    job: Mapped[Job] = relationship(back_populates="features")

    def as_dict(self) -> dict:
        """Forme attendue par ``ananas.ai.matching.score_job``."""
        return {
            "role_family": self.role_family,
            "seniority": self.seniority,
            "years_experience_min": self.years_experience_min,
            "contract": self.contract,
            "remote": self.remote,
            "skills": self.skills or [],
            "nice_to_have": self.nice_to_have or [],
            "domains": self.domains or [],
            "languages": self.languages or [],
            "locations": self.locations or [],
            "summary": self.summary,
        }


class ExtractionBatch(Base):
    """Un lot de caracterisation d'offres soumis au fournisseur de modele.

    Soumis vers minuit, recolte au matin (voir ``ananas.ai.service`` et
    ``ananas.worker.main``). Persiste plutot que garde en memoire: le worker
    tourne en demon, mais un redemarrage entre les deux passes ne doit ni
    perdre le lot en cours ni le resoumettre en double — d'ou aussi
    ``job_ids``, qui sert a exclure ces offres d'un nouveau lot tant que
    celui-ci n'est pas recolte.
    """

    __tablename__ = "extraction_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Cle du BaseLLM ayant soumis le lot (voir ai/registry.py)
    provider: Mapped[str] = mapped_column(String(32))
    # Identifiant renvoye par le fournisseur (ex. "batches/xxxxx" chez Gemini)
    provider_batch_id: Mapped[str] = mapped_column(String(255))
    # Offres soumises, dans l'ordre exact envoye au fournisseur: les resultats
    # d'un lot inline reviennent alignes par position, pas par cle.
    job_ids: Mapped[list] = mapped_column(JSON, default=list)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # 'pending' -> 'collected' (resultats appliques, meme partiellement) ou
    # 'failed' (lot entier perdu: JOB_STATE_FAILED/CANCELLED/EXPIRED chez
    # Gemini). Dans les deux cas les offres non caracterisees repartent
    # naturellement dans le prochain lot, puisqu'elles restent sans
    # JobFeatures.
    status: Mapped[str] = mapped_column(
        String(16), default="pending", server_default="pending", index=True
    )
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UserProfile(Base):
    """CV et aspirations d'un utilisateur, plus leur forme structuree.

    ``version`` s'incremente a chaque nouvelle extraction: c'est ce qui permet
    de savoir quels scores sont perimes sans tout recalculer aveuglement.
    """

    __tablename__ = "user_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    cv_text: Mapped[str] = mapped_column(Text, default="")
    aspirations: Mapped[str] = mapped_column(Text, default="")

    # Resultat de l'extraction, meme vocabulaire que JobFeatures
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=0)
    model: Mapped[str] = mapped_column(String(80), default="")
    extracted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # 'ok' | 'error' | None tant qu'aucune extraction n'a eu lieu
    status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Seuil au-dela duquel une offre est jugee pertinente pour cette personne
    match_threshold: Mapped[int] = mapped_column(Integer, default=55, server_default="55")
    # Ne notifier que les offres au-dessus du seuil
    notify_only_relevant: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship()

    @property
    def is_ready(self) -> bool:
        return bool(self.data) and self.status == "ok"


class UserHome(Base):
    """Domicile de reference d'un utilisateur, et rayon de recherche associe.

    Table separee de ``user_profiles`` a dessein: le profil est jetable —
    ``DELETE /api/me/profile`` l'efface pour reanalyser un CV — alors qu'une
    adresse de domicile est saisie a la main une fois pour toutes. La ranger
    la-bas ferait perdre l'adresse a chaque remise a zero du CV.

    Les coordonnees sont geocodees a l'enregistrement (Nominatim, comme les
    entreprises) et stockees: la distance a chaque entreprise se calcule
    ensuite sans appel reseau.
    """

    __tablename__ = "user_homes"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    street: Mapped[str] = mapped_column(String(255), default="", server_default="")
    postal_code: Mapped[str] = mapped_column(String(16), default="", server_default="")
    city: Mapped[str] = mapped_column(String(120), default="", server_default="")
    country: Mapped[str] = mapped_column(String(80), default="Belgium", server_default="Belgium")
    # Adresse recomposee, telle qu'affichee a l'utilisateur
    address: Mapped[str] = mapped_column(String(500), default="", server_default="")

    # NULL tant que le geocodage n'a rien trouve: l'interface le dit plutot que
    # de placer un cercle au hasard.
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Meme vocabulaire que Company.geo_precision ('adresse' | 'ville' | ...)
    geo_precision: Mapped[str] = mapped_column(String(32), default="", server_default="")

    # Rayon du perimetre de recherche, en kilometres. Sert de valeur par defaut
    # aux filtres et au cercle trace sur la carte.
    radius_km: Mapped[int] = mapped_column(Integer, default=25, server_default="25")

    # Appliquer ce rayon a la notification quotidienne. False par defaut, a
    # l'inverse de ``notify_only_relevant``: le seuil de pertinence se regle
    # juste apres avoir vu son profil analyse, alors qu'un rayon sert d'abord a
    # regarder la carte. En faire un filtre d'envoi sans le demander ferait
    # disparaitre des offres sans que personne l'ait decide.
    notify_within_radius: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship()

    @property
    def point(self) -> tuple[float, float] | None:
        """(lat, lon) quand le domicile est localise — la forme attendue par
        ``ananas.distance.distance_from``."""
        return None if self.lat is None or self.lon is None else (self.lat, self.lon)


class JobMatch(Base):
    """Score d'une offre pour un utilisateur.

    Materialise parce que le calcul est gratuit mais pas instantane a l'echelle
    de toutes les paires, et surtout pour pouvoir trier et filtrer en SQL —
    c'est ce qui permet "les offres pertinentes de cette entreprise".
    """

    __tablename__ = "job_matches"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True)
    score: Mapped[int] = mapped_column(Integer, index=True)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    # Version du profil ayant servi au calcul: un score plus ancien est perime
    profile_version: Mapped[int] = mapped_column(Integer, default=0)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class HiddenJob(Base):
    """Une offre que l'utilisateur a explicitement ecartee.

    Meme forme que ``SavedCompany``: la PK composite (user_id, job_id) rend le
    masquage idempotent (le cacher deux fois n'est pas une erreur) et sert
    directement de test d'appartenance dans le filtre de ``GET /api/me/jobs``.

    N'affecte que l'affichage. La notification quotidienne ne repose pas sur
    cette table: c'est ``sent_job_notifications`` qui garantit deja qu'une
    offre n'est jamais notifiee deux fois, masquee ou non.
    """

    __tablename__ = "hidden_jobs"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True)
    hidden_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SentJobNotification(Base):
    """Trace d'idempotence: cet utilisateur a deja ete prevenu de cette offre.

    La PK composite est la garantie anti-doublon. Relancer le worker dix fois
    dans la journee n'enverra jamais deux fois la meme offre.
    """

    __tablename__ = "sent_job_notifications"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    channel_type: Mapped[str] = mapped_column(String(32), default="telegram")


class TelegramLinkCode(Base):
    """Code a usage unique liant un compte Ananas a une conversation Telegram.

    Un bot Telegram ne peut pas ecrire a quelqu'un qui ne lui a jamais parle:
    c'est donc l'utilisateur qui doit initier. Le code voyage dans le lien
    profond ``https://t.me/<bot>?start=<code>``, l'utilisateur appuie sur
    "Demarrer", et le serveur retrouve le ``chat.id`` dans la mise a jour
    correspondante.

    Cela evite surtout d'avoir a communiquer le token du bot a l'utilisateur:
    c'est un secret serveur partage par tous les comptes.
    """

    __tablename__ = "telegram_link_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Rempli quand la mise a jour Telegram correspondante a ete vue
    chat_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    user: Mapped[User] = relationship()


class AppState(Base):
    """Petites valeurs de service qui doivent survivre a un redemarrage.

    Sert au curseur ``telegram_update_offset``: l'API de Telegram ne rejoue une
    mise a jour que tant qu'elle n'a pas ete confirmee par un offset superieur.
    Perdre ce curseur ferait retraiter, ou pire manquer, des liaisons.
    """

    __tablename__ = "app_state"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


class ScrapeRun(Base):
    """Une execution du worker — de quoi savoir si le run de la nuit a marche."""

    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    companies_total: Mapped[int] = mapped_column(Integer, default=0)
    companies_ok: Mapped[int] = mapped_column(Integer, default=0)
    companies_failed: Mapped[int] = mapped_column(Integer, default=0)
    jobs_new: Mapped[int] = mapped_column(Integer, default=0)
    jobs_closed: Mapped[int] = mapped_column(Integer, default=0)
    notifications_sent: Mapped[int] = mapped_column(Integer, default=0)
