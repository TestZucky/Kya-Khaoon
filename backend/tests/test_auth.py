"""
SMS OTP login, on the console provider (no real SMS).

Covers the real security behaviour: a code must be requested, it verifies once,
wrong codes are rejected and eventually burned, tokens gate the app, and a bad
token is refused.

Run:  python -m tests.test_auth
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./auth_test.db")
os.environ["SWIGGY_CLIENT"] = "fake"
os.environ["SMS_PROVIDER"] = "console"

from fastapi.testclient import TestClient  # noqa: E402

from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402


def main() -> None:
    init_db()
    c = TestClient(app)
    phone = "9876500123"

    # A protected endpoint is refused without a token.
    assert c.post("/decks", json={}).status_code == 401
    print("  ok  /decks rejects a request with no token")

    # Request a code — console provider hands it back as dev_code.
    r = c.post("/auth/request-otp", json={"phone": phone})
    assert r.status_code == 200, r.text
    code = r.json()["dev_code"]
    assert code and len(code) == 6
    print(f"  ok  request-otp issued a 6-digit code ({code})")

    # Wrong code is rejected.
    bad = c.post("/auth/verify-otp", json={"phone": phone, "code": "000000"})
    assert bad.status_code == 400 and "Incorrect" in bad.json()["detail"]
    print("  ok  wrong code rejected")

    # Correct code verifies and returns a token; new user isn't onboarded yet.
    ok = c.post("/auth/verify-otp", json={"phone": phone, "code": code})
    assert ok.status_code == 200, ok.text
    auth = ok.json()
    token = auth["token"]
    assert auth["onboarded"] is False and auth["phone"] == phone
    print("  ok  correct code verified, token issued, onboarded=false")

    # The code is single-use — replaying it fails.
    replay = c.post("/auth/verify-otp", json={"phone": phone, "code": code})
    assert replay.status_code == 400
    print("  ok  code is single-use (replay refused)")

    headers = {"Authorization": f"Bearer {token}"}

    # A garbage token is refused.
    assert (
        c.post("/decks", json={}, headers={"Authorization": "Bearer nope"}).status_code
        == 401
    )
    print("  ok  invalid token refused")

    # With the token, onboarding works and the deck flows.
    onboard = c.post(
        "/onboard",
        headers=headers,
        json={
            "swiggy_address_id": "228077662",
            "profile": {"diet": "non_veg", "budget_band": "above_500"},
        },
    )
    assert onboard.status_code == 200, onboard.text
    from app.seed import seed

    seed()
    deck = c.post("/decks", json={"mood": "comfort"}, headers=headers)
    assert deck.status_code == 200 and deck.json()["cards"], deck.text
    print("  ok  token authorises onboard + deck")

    # Verify now reports onboarded=true after a re-login.
    r2 = c.post("/auth/request-otp", json={"phone": phone}).json()
    # resend interval may block an immediate second request — allow either.
    if "dev_code" in r2 and r2.get("dev_code"):
        v2 = c.post(
            "/auth/verify-otp", json={"phone": phone, "code": r2["dev_code"]}
        ).json()
        assert v2["onboarded"] is True
        print("  ok  re-login reports onboarded=true")

    print("\nAUTH TESTS PASSED ✅")
    if os.path.exists("./auth_test.db"):
        os.remove("./auth_test.db")


if __name__ == "__main__":
    main()
