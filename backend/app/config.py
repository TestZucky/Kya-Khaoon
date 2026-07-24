from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# The single .env at the repo root (backend/app/config.py → ../../.env).
_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    # Reads the root .env, but real env vars (Docker, shell) still win over it.
    model_config = SettingsConfigDict(env_file=_ROOT_ENV, extra="ignore")

    database_url: str = "postgresql+psycopg://kya:kya@localhost:5432/kya_khaoon"

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
    # is always allowed; this is for tunnels (ngrok) and deployed builds.
    extra_cors_origins: str = ""

    # No key configured → the recommender falls back to the deterministic rules.
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_timeout: float = 30.0

    # Signs session tokens. MUST be overridden in production.
    secret_key: str = "dev-insecure-change-me"
    session_ttl_hours: int = 720  # 30 days

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

    @property
    def cors_origins_list(self) -> list[str]:
        origins = [self.frontend_url.rstrip("/")]
        origins += [o.strip().rstrip("/") for o in self.extra_cors_origins.split(",")]
        return [o for o in dict.fromkeys(origins) if o]


@lru_cache
def get_settings() -> Settings:
    return Settings()
