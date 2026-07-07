from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    database_url: str = "sqlite+aiosqlite:///./baksignal.db"
    telegram_bot_token: str | None = None
    mini_app_url: str | None = None
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    status_fresh_minutes: int = Field(default=60, ge=1)
    status_stale_minutes: int = Field(default=120, ge=1)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
