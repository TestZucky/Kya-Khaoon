"""
Google Sign-In — verification logic, mocked (no real Google token needed).

Proves: a valid token creates/returns a user + issues a session token that gates
the app; a token minted for a different app (wrong `aud`) is rejected.

Run:  python -m tests.test_google
"""

import os

from tests.dbsetup import fresh_db, use_test_db  # noqa: E402

use_test_db()
os.environ["SWIGGY_CLIENT"] = "fake"
os.environ["GOOGLE_CLIENT_ID"] = "my-app.apps.googleusercontent.com"

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import google  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402

get_settings.cache_clear()


class _Resp:
    def __init__(self, status: int, payload: dict) -> None:
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload


VALID = {
    "aud": "my-app.apps.googleusercontent.com",
    "iss": "https://accounts.google.com",
    "sub": "google-user-123",
    "email": "arjun@example.com",
    "name": "Arjun Sharma",
}


def main() -> None:
    fresh_db()
    c = TestClient(app)

    # --- valid token → user created, token gates the app ---
    async def _ok(self, url, params=None):
        return _Resp(200, VALID)

    import httpx

    orig = httpx.AsyncClient.get
    httpx.AsyncClient.get = _ok  # type: ignore[assignment]
    try:
        r = c.post("/auth/google", json={"id_token": "whatever"})
        assert r.status_code == 200, r.text
        auth = r.json()
        assert auth["onboarded"] is False and auth["token"]
        print("  ok  valid Google token → user created, session issued")

        headers = {"Authorization": f"Bearer {auth['token']}"}
        assert c.post("/decks", json={}, headers=headers).status_code in (200, 400)
        assert c.post("/decks", json={}).status_code == 401
        print("  ok  the session token authorises; missing token is refused")

        # Same sub logs into the SAME user (no duplicate).
        r2 = c.post("/auth/google", json={"id_token": "whatever"})
        assert r2.json()["user_id"] == auth["user_id"]
        print("  ok  repeat sign-in returns the same user")
    finally:
        httpx.AsyncClient.get = orig  # type: ignore[assignment]

    # --- wrong audience → rejected ---
    async def _wrong_aud(self, url, params=None):
        return _Resp(200, {**VALID, "aud": "someone-else.apps.googleusercontent.com"})

    httpx.AsyncClient.get = _wrong_aud  # type: ignore[assignment]
    try:
        bad = c.post("/auth/google", json={"id_token": "stolen"})
        assert bad.status_code == 401, bad.text
        print("  ok  token for another app (wrong aud) rejected")
    finally:
        httpx.AsyncClient.get = orig  # type: ignore[assignment]

    _ = google  # (module imported for coverage/clarity)
    print("\nGOOGLE AUTH TESTS PASSED ✅")
    if os.path.exists("./google_test.db"):
        os.remove("./google_test.db")


if __name__ == "__main__":
    main()
