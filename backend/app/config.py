"""Настройки сервера. Значения читаются из переменных окружения и файла .env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent  # папка backend/
DEV_SECRET = "dev-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    database_url: str = f"sqlite:///{BASE_DIR / 'vmeste.db'}"
    secret_key: str = DEV_SECRET
    access_token_minutes: int = 30
    refresh_token_days: int = 60

    media_dir: str = str(BASE_DIR / "media")
    max_avatar_mb: int = 5

    auto_create_tables: bool = True
    run_scheduler: bool = True
    reminder_interval_minutes: int = 15
    risk_hour: int = 20

    admin_username: str = "admin"
    admin_password: str = ""

    @property
    def sqlalchemy_url(self) -> str:
        # Драйвер psycopg 3: «postgresql://» в SQLAlchemy по умолчанию означает psycopg2.
        url = self.database_url
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://") :]
        return url

    @property
    def is_sqlite(self) -> bool:
        return self.sqlalchemy_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.environment == "production" and (
        settings.secret_key == DEV_SECRET or len(settings.secret_key) < 32
    ):
        raise RuntimeError(
            "В production нужен SECRET_KEY длиной не менее 32 символов "
            '(python -c "import secrets; print(secrets.token_urlsafe(48))")'
        )
    return settings
