"""
CleanTrack AI — Application Configuration
Reads from environment variables / .env file using Pydantic Settings.
"""
from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ──────────────────────────────────────────────────────
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = False
    allowed_origins: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    # ── Database ─────────────────────────────────────────────────
    database_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # ── Redis ────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── JWT ──────────────────────────────────────────────────────
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # ── Storage ──────────────────────────────────────────────────
    storage_endpoint_url: str = "http://localhost:9000"
    storage_access_key: str = "minioadmin"
    storage_secret_key: str = "minioadmin"
    storage_bucket_photos: str = "cleantrack-photos"
    storage_bucket_thumbs: str = "cleantrack-thumbs"
    storage_region: str = "us-east-1"
    storage_public_base_url: str = "http://localhost:9000/cleantrack-photos"

    # ── AI Service ───────────────────────────────────────────────
    ai_service_url: str = "http://localhost:8001"
    ai_service_timeout_seconds: int = 30

    # ── Google Maps ──────────────────────────────────────────────
    google_maps_api_key: str = ""

    # ── Firebase ─────────────────────────────────────────────────
    firebase_credentials_path: str = "./firebase-credentials.json"
    firebase_credentials_base64: str = ""

    # ── Twilio SMS ────────────────────────────────────────────────
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    # ── AI Thresholds ─────────────────────────────────────────────
    dedup_radius_meters: float = 50.0
    dedup_window_hours: int = 72
    hotspot_radius_meters: float = 200.0
    hotspot_min_reports: int = 3
    hotspot_window_days: int = 7

    # ── Rate Limiting ─────────────────────────────────────────────
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # ── Logging ──────────────────────────────────────────────────
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton — call this everywhere."""
    return Settings()
