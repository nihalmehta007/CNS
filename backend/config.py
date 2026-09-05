"""
backend/config.py — Centralised application settings.

All configuration is loaded from environment variables (or a .env file
in the project root).  Every other module imports `settings` from here
instead of calling ``os.environ.get()`` directly.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List

from pydantic import field_validator
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
    CORS_ORIGINS: List[str] = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        """Support comma-separated string or JSON array in env vars, stripping trailing slashes."""
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                try:
                    return [str(orig).strip().rstrip("/") for orig in json.loads(v) if str(orig).strip()]
                except Exception:
                    pass
            return [orig.strip().rstrip("/") for orig in v.split(",") if orig.strip()]
        if isinstance(v, (list, tuple, set)):
            return [str(orig).strip().rstrip("/") for orig in v if str(orig).strip()]
        return v

    # ── Rate limiting ────────────────────────────────────────────────
    RATE_LIMIT_MAX: int = 5
    RATE_LIMIT_WINDOW: int = 600          # seconds (10 minutes)

    # ── Request size ─────────────────────────────────────────────────
    MAX_BODY_SIZE: int = 1_048_576        # 1 MB

    # ── Secret key (CSRF signing) ────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production"

    # ── Mail (SMTP) ──────────────────────────────────────────────────
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_PORT: int = 587
    MAIL_USERNAME: str = "crimsonnyxstudios@gmail.com"
    MAIL_PASSWORD: str = ""               # Gmail App Password (required)
    MAIL_RECIPIENT: str = "crimsonnyxstudios@gmail.com"
    MAIL_ENABLED: bool = True             # auto-disabled if password is empty


settings = Settings()

# Auto-disable mail if no password is configured
if not settings.MAIL_PASSWORD:
    settings.MAIL_ENABLED = False
