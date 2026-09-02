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

    # --- notifications
    telegram_bot_token: str = ""

    # --- worker
    scrape_cron_hour: int = 6
    scrape_cron_minute: int = 0
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
