from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: Literal["dev", "staging", "prod"] = "dev"
    dev_tools_enabled: bool = False

    database_url: str = Field(
        default="postgresql+asyncpg://khushhal:khushhal@localhost:5432/khushhal"
    )

    # Kept as a raw comma-separated string so pydantic-settings doesn't try
    # to JSON-parse it from .env. Callers consume `cors_origins`.
    cors_origins_raw: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")

    firebase_credentials_json: str = ""

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]

    @property
    def is_dev(self) -> bool:
        return self.env == "dev"


@lru_cache
def get_settings() -> Settings:
    return Settings()
