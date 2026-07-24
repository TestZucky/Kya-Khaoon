from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Secrets that ship in this repo's examples and defaults. Fine on a laptop,
# fatal anywhere real — they're public knowledge by definition.
_PUBLIC_SECRETS = {
    "dev-secret",
    "dev-insecure-change-me",
    "changeme",
    "secret",
    "test",
}

# The compose credentials. Also public knowledge.
_DEV_DB_CREDENTIALS = "kya:kya@"

# The single .env at the repo root (backend/app/config.py → ../../.env).
_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    # Reads the root .env, but real env vars (Docker, shell) still win over it.
    model_config = SettingsConfigDict(env_file=_ROOT_ENV, extra="ignore")

    # "prod" for anything a real user can reach; "dev" on a laptop and in CI.
    # prod turns on the startup checks at the bottom of this file, which refuse
    # to boot on a configuration that would leak or be trivially broken into.
    #
    # It defaults to prod and compose sets it back to dev, rather than the other
    # way round: forgetting an env var should cost you a loud failure on your
    # laptop, never a quietly unguarded deployment.
    app_env: Literal["dev", "prod"] = "prod"

    # `db` is the compose service name — everything runs in containers, so the
    # database is a network hop away, never localhost.
    database_url: str = "postgresql+psycopg://kya:kya@db:5432/kya_khaoon"

    log_level: Literal["debug", "info", "warning", "error"] = "info"

    swiggy_client: Literal["fake", "mcp"] = "fake"

    # The remote Swiggy MCP server's Streamable HTTP endpoint (the URL you OAuth
    # against). Each user's own bearer token is sent per request; a static token
    # may be set for single-account testing.
    swiggy_mcp_url: str = ""
    swiggy_mcp_static_token: str = ""
    swiggy_mcp_timeout: float = 15.0

    # Swiggy OAuth (OAuth 2.1 + PKCE + Dynamic Client Registration).
    swiggy_oauth_base: str = "https://mcp.swiggy.com"
    swiggy_redirect_uri: str = "http://localhost:8000/auth/swiggy/callback"
    # Where to bounce the browser after a successful connect.
    frontend_url: str = "http://localhost:5173"
    # Extra browser origins allowed to call the API, comma-separated. frontend_url
    # is always allowed; this is for deployed builds on other origins.
    extra_cors_origins: str = ""

    # No key configured → the recommender falls back to the deterministic rules.
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_timeout: float = 30.0

    # Signs session tokens. MUST be overridden in production.
    secret_key: str = "dev-insecure-change-me"
    session_ttl_hours: int = 720  # 30 days

    # Encrypts the Swiggy credentials we hold on each user's behalf (app/crypto.py).
    # Comma-separated to rotate: the first key encrypts, all of them can decrypt.
    # Empty derives a key from secret_key, so dev and CI need no extra setup.
    token_encryption_key: str = ""

    # Device sign-in creates users with nothing verified, and a new user can
    # trigger a paid deck generation — so cap how many one IP can mint.
    device_signup_window_seconds: int = 3600
    device_signup_max_per_window: int = 20

    # "console" logs the code (dev, no SMS); "twilio" sends a real SMS.
    sms_provider: Literal["console", "twilio"] = "console"
    otp_length: int = 6
    otp_ttl_seconds: int = 300
    otp_max_attempts: int = 5  # wrong tries before a code is burned
    otp_resend_interval_seconds: int = 30

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from: str = ""

    # Google Sign-In web client id (public). ID tokens must carry it as `aud`.
    google_client_id: str = ""

    @field_validator("database_url")
    @classmethod
    def _must_be_postgres(cls, v: str) -> str:
        # Postgres is the only supported database. A stale sqlite:// URL in a
        # leftover .env would otherwise start fine and then behave subtly
        # differently from CI and prod — fail loudly at import instead.
        if not v.startswith(("postgresql://", "postgresql+psycopg://")):
            raise ValueError(
                f"DATABASE_URL must be a postgresql:// URL (got {v.split('://')[0]}://…). "
                "Postgres is the only supported database."
            )
        return v

    @model_validator(mode="after")
    def _production_must_be_configured(self) -> "Settings":
        """
        Refuse to start a production instance on a dev configuration.

        Every one of these is a real hole rather than untidiness, so they fail
        rather than warn — a warning in a startup log is a warning nobody reads.
        They're collected and raised together so one deploy tells you everything
        that's wrong, instead of one round-trip per problem.
        """
        if self.app_env != "prod":
            return self

        problems: list[str] = []

        if self.secret_key in _PUBLIC_SECRETS or len(self.secret_key) < 32:
            problems.append(
                "SECRET_KEY is a known dev value or under 32 chars — it signs every "
                "session token, so anyone who guesses it can mint a session for any "
                "user. Generate one with: python -c \"import secrets; "
                'print(secrets.token_urlsafe(48))"'
            )

        if not self.token_encryption_key.strip():
            problems.append(
                "TOKEN_ENCRYPTION_KEY is unset, so the Swiggy tokens fall back to a key "
                "derived from SECRET_KEY — rotating one would then silently disconnect "
                "every user. Generate one with: python -c \"from cryptography.fernet "
                'import Fernet; print(Fernet.generate_key().decode())"'
            )

        if self.sms_provider == "console":
            problems.append(
                "SMS_PROVIDER=console returns the OTP in the /auth/request-otp response "
                "body — anyone could sign in as any phone number. Configure twilio."
            )

        if _DEV_DB_CREDENTIALS in self.database_url:
            problems.append(
                "DATABASE_URL still carries the compose credentials (kya:kya), which are "
                "published in this repo."
            )

        for name, url in (
            ("SWIGGY_REDIRECT_URI", self.swiggy_redirect_uri),
            ("FRONTEND_URL", self.frontend_url),
        ):
            parsed = urlparse(url)
            if parsed.scheme != "https" or parsed.hostname in ("localhost", "127.0.0.1"):
                problems.append(f"{name} must be an https:// URL on a real host (got {url!r}).")

        if problems:
            raise ValueError(
                "refusing to start with APP_ENV=prod:\n  - " + "\n  - ".join(problems)
            )
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        origins = [self.frontend_url.rstrip("/")]
        origins += [o.strip().rstrip("/") for o in self.extra_cors_origins.split(",")]
        return [o for o in dict.fromkeys(origins) if o]


@lru_cache
def get_settings() -> Settings:
    return Settings()
