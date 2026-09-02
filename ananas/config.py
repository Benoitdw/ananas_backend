"""Configuration lue depuis l'environnement (voir .env.example a la racine)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://ananas:ananas@localhost:5432/ananas"

    # --- securite
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 30
    cookie_name: str = "ananas_session"
    # False en dev (http://localhost), True derriere HTTPS en production
    cookie_secure: bool = False
    cors_origins: str = "http://localhost:5173"

    # --- compte d'administration (voir `python -m ananas.admin`)
    # Lu uniquement par cette commande: l'API ne s'en sert jamais, et aucune
    # route ne peut promouvoir un compte. Le mot de passe n'est donc present
    # que dans le .env, jamais en base en clair ni dans un JWT.
    admin_email: str = ""
    admin_password: str = ""

    # --- notifications
    telegram_bot_token: str = ""

    # --- modele de langage
    # Sert uniquement a structurer du texte libre (offres, CV). La comparaison
    # profil/offre est du Python deterministe: changer de fournisseur, y compris
    # pour un modele local, ne touche que ananas/ai/.
    ai_provider: str = "gemini"
    ai_model: str = "gemini-3.7-flash"
    ai_timeout: int = 60
    gemini_api_key: str = ""
    # En dessous de ce score (0-100) une offre n'est pas jugee pertinente
    match_threshold_default: int = 55

    # --- worker
    # Passe de scrape + soumission du lot d'extraction (voir ananas.ai.service).
    # Par defaut minuit: laisse toute la nuit au lot pour se terminer avant la
    # notification du matin — dont l'heure est independante, voir
    # notify_cron_hour/minute.
    scrape_cron_hour: int = 0
    scrape_cron_minute: int = 0
    # Recolte du lot (partielle si besoin) + notification quotidienne.
    notify_cron_hour: int = 7
    notify_cron_minute: int = 0
    timezone: str = "Europe/Brussels"
    # Pause entre deux entreprises scrapees, en secondes
    scrape_delay: float = 1.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
