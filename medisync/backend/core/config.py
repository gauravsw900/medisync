"""
Application configuration.

All settings are read from environment variables — never hardcoded.
In development, these come from a .env file loaded by python-dotenv.
In production (Docker), they're passed as environment variables.

Using Pydantic Settings ensures type safety and validation at startup —
if a required variable is missing, the app fails immediately with a
clear error rather than failing later with a cryptic message.
"""

from pydantic_settings import BaseSettings
from typing import list


class Settings(BaseSettings):
    # ── Database ───────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql://medisync:medisync123@localhost:5432/medisync"

    # ── JWT Authentication ─────────────────────────────────────────────────────
    # Secret key used to sign JWT tokens. Must be kept secret in production.
    # Generate a secure one with: python -c "import secrets; print(secrets.token_hex(32))"
    SECRET_KEY: str = "dev-secret-key-change-in-production-minimum-32-characters"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Anthropic ──────────────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""

    # ── Application ────────────────────────────────────────────────────────────
    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "MediSync"
    API_V1_PREFIX: str = "/api/v1"

    # CORS origins — frontend URLs allowed to call the API
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True


# Single shared instance — imported everywhere
settings = Settings()
