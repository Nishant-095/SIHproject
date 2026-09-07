from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Airfare APIx"
    app_env: Literal["development", "test", "production"] = "development"
    app_version: str = "0.1.0"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://airfare:airfare@localhost:5432/airfare_apix"

    collection_timezone: str = "Asia/Kolkata"
    collection_hour: int = Field(default=10, ge=0, le=23)
    collection_minute: int = Field(default=0, ge=0, le=59)
    scheduler_enabled: bool = False
    scheduled_source: Literal["fixture", "duffel", "permissioned_web"] = "fixture"

    adapter_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    adapter_max_retries: int = Field(default=2, ge=0, le=2)
    retry_backoff_seconds: float = Field(default=0.5, ge=0, le=30)
    retry_backoff_max_seconds: float = Field(default=4.0, ge=0, le=60)
    enforce_source_rate_limits: bool = True
    canonical_fare_policy: Literal["direct-then-median-v1", "approved-source-median-v1"] = (
        "direct-then-median-v1"
    )

    duffel_api_base_url: str = "https://api.duffel.com"
    duffel_access_token: SecretStr | None = None
    duffel_live_mode: bool = False
    duffel_source_enabled: bool = False
    duffel_source_approved: bool = False
    duffel_rate_limit_per_minute: int = Field(default=5, ge=1, le=60)
    duffel_supplier_timeout_ms: int = Field(default=20_000, ge=2_000, le=60_000)

    web_source_profile_path: Path | None = None
    web_source_enabled: bool = False
    web_source_approved: bool = False
    web_source_permission_reference: str | None = Field(default=None, max_length=300)
    web_source_user_agent: str = Field(
        default="AirfareAPIxResearchBot/0.1 (permissioned academic fare collection)",
        min_length=10,
        max_length=300,
    )
    web_source_rate_limit_per_minute: int = Field(default=2, ge=1, le=30)
    web_source_browser_timeout_ms: int = Field(default=25_000, ge=2_000, le=90_000)

    admin_token: str = "change-me-before-use"
    cors_origins: list[str] = ["http://localhost:5173"]

    @field_validator("duffel_access_token", mode="before")
    @classmethod
    def blank_duffel_token_is_unset(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("web_source_profile_path", "web_source_permission_reference", mode="before")
    @classmethod
    def blank_web_source_setting_is_unset(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
