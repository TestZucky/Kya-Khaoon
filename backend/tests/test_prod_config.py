"""
APP_ENV=prod refuses to boot on a dev configuration.

Each of these is a real hole, not a style preference, so the test asserts the
*reason* is reported and not merely that something failed — a guard that fires
for the wrong reason is a guard that will be silenced.

Settings is constructed directly (no engine, no database), and every relevant
field is passed explicitly so the surrounding container's env can't colour the
result.

Run:  python -m tests.test_prod_config
"""

from pydantic import ValidationError

from app.config import Settings

# A configuration that should be allowed to start.
GOOD = {
    "app_env": "prod",
    "secret_key": "s" * 48,
    "token_encryption_key": "Zm9vYmFyYmF6cXV4Zm9vYmFyYmF6cXV4Zm9vYmFyYmE=",
    "sms_provider": "twilio",
    "database_url": "postgresql+psycopg://kya:a-real-password@db.internal:5432/kya",
    "swiggy_redirect_uri": "https://kyakhaoon.example/auth/swiggy/callback",
    "frontend_url": "https://kyakhaoon.example",
}


def _problem(**overrides) -> str:
    """Build a prod Settings that should fail, and return the message."""
    try:
        Settings(**{**GOOD, **overrides}, _env_file=None)
    except ValidationError as e:
        return str(e)
    raise AssertionError(f"expected {overrides} to be refused, but it started")


def main() -> None:
    # The baseline has to pass, or every assertion below proves nothing.
    Settings(**GOOD, _env_file=None)
    print("  ok  a properly configured prod instance starts")

    assert "SECRET_KEY" in _problem(secret_key="dev-secret")
    assert "SECRET_KEY" in _problem(secret_key="short")
    print("  ok  a dev or too-short SECRET_KEY is refused")

    assert "TOKEN_ENCRYPTION_KEY" in _problem(token_encryption_key="")
    print("  ok  an underived token encryption key is required")

    assert "OTP" in _problem(sms_provider="console")
    print("  ok  console OTP delivery is refused (it returns the code)")

    assert "kya:kya" in _problem(
        database_url="postgresql+psycopg://kya:kya@db:5432/kya_khaoon"
    )
    print("  ok  the published compose database password is refused")

    assert "SWIGGY_REDIRECT_URI" in _problem(
        swiggy_redirect_uri="http://localhost:8000/auth/swiggy/callback"
    )
    assert "FRONTEND_URL" in _problem(frontend_url="http://localhost:5173")
    print("  ok  localhost and plain http URLs are refused")

    # Everything wrong at once should be reported at once — one deploy, one fix.
    everything = _problem(
        secret_key="dev-secret",
        token_encryption_key="",
        sms_provider="console",
        frontend_url="http://localhost:5173",
    )
    for expected in ("SECRET_KEY", "TOKEN_ENCRYPTION_KEY", "OTP", "FRONTEND_URL"):
        assert expected in everything
    print("  ok  every problem is reported together, not one per deploy")

    # And none of it applies on a laptop.
    Settings(app_env="dev", secret_key="dev-secret", sms_provider="console", _env_file=None)
    print("  ok  dev is left alone")

    print("\nPROD CONFIG GUARD TESTS PASSED ✅")


if __name__ == "__main__":
    main()
