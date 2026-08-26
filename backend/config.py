"""
backend/config.py — Centralised application settings.

All configuration is loaded from environment variables (or a .env file
in the project root).  Every other module imports `settings` from here
instead of calling ``os.environ.get()`` directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


_PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Application-wide configuration."""

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────
    APP_ENV: str = "development"  # "development" | "production"

    # ── MongoDB ──────────────────────────────────────────────────────
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB: str = "crimson_nyx"
    MONGO_POOL_SIZE: int = 10
    MONGO_TIMEOUT_MS: int = 5_000

    # ── Admin credentials ────────────────────────────────────────────
    # ADMIN_PASS_HASH should be a bcrypt hash produced with:
    #   python -c "from passlib.hash import bcrypt; print(bcrypt.hash('yourpass'))"
    # When ADMIN_PASS_HASH is set it takes precedence over ADMIN_PASS.
    ADMIN_USER: str = "admin"
    ADMIN_PASS: str = "admin123"          # plaintext fallback (dev only)
    ADMIN_PASS_HASH: str = ""             # bcrypt hash (preferred in prod)

    # ── CORS ─────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = ["http://localhost:8001", "http://127.0.0.1:8001"]

    # ── Rate limiting ────────────────────────────────────────────────
    RATE_LIMIT_MAX: int = 5
    RATE_LIMIT_WINDOW: int = 600          # seconds (10 minutes)

    # ── Request size ─────────────────────────────────────────────────
    MAX_BODY_SIZE: int = 1_048_576        # 1 MB


settings = Settings()
