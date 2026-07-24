"""
Device-id sign-in.

Proves: a device id creates a user and issues a session token that gates the app;
the same id comes back to the same user (this is the whole persistence claim); a
different id is a different user; junk ids are rejected; and the per-IP signup
cap holds so an unauthenticated loop can't mint users (and paid deck calls).

Run:  python -m tests.test_device
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./device_test.db")
os.environ["SWIGGY_CLIENT"] = "fake"

from fastapi.testclient import TestClient  # noqa: E402

from app.auth.device import reset_rate_limits  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402

get_settings.cache_clear()

DEVICE_A = "11111111-2222-3333-4444-555555555555"
DEVICE_B = "99999999-8888-7777-6666-555555555555"


def main() -> None:
    init_db()
    reset_rate_limits()
    c = TestClient(app)

    # --- first sign-in creates a user ---
    r = c.post("/auth/device", json={"device_id": DEVICE_A})
    assert r.status_code == 200, r.text
    auth = r.json()
    assert auth["token"] and auth["user_id"]
    assert auth["onboarded"] is False
    print("  ok  new device id creates a user + session")

    # --- the token actually gates a protected route ---
    headers = {"Authorization": f"Bearer {auth['token']}"}
    me = c.get("/addresses", headers=headers)
    assert me.status_code == 200, me.text
    assert c.get("/addresses").status_code == 401
    print("  ok  issued token gates protected routes")

    # --- same device id → same user (the persistence guarantee) ---
    again = c.post("/auth/device", json={"device_id": DEVICE_A})
    assert again.status_code == 200, again.text
    assert again.json()["user_id"] == auth["user_id"]
    print("  ok  same device id returns the same user")

    # --- profile written on one call is visible on the next session ---
    c.post(
        "/onboard",
        json={"profile": {"diet": "veg", "cuisines": ["north_indian"]}},
        headers=headers,
    )
    back = c.post("/auth/device", json={"device_id": DEVICE_A})
    assert back.json()["onboarded"] is True
    print("  ok  profile persists across sign-ins")

    # --- a different device id is a different user ---
    other = c.post("/auth/device", json={"device_id": DEVICE_B})
    assert other.status_code == 200, other.text
    assert other.json()["user_id"] != auth["user_id"]
    assert other.json()["onboarded"] is False
    print("  ok  a different device id is a different user")

    # --- junk ids rejected (too short to be unguessable) ---
    bad = c.post("/auth/device", json={"device_id": "abc"})
    assert bad.status_code == 422, bad.text
    print("  ok  too-short device id rejected")

    # --- per-IP signup cap: new ids are throttled, known ones are not ---
    reset_rate_limits()
    limit = get_settings().device_signup_max_per_window
    for i in range(limit):
        ok = c.post("/auth/device", json={"device_id": f"flood-device-id-{i:04d}"})
        assert ok.status_code == 200, ok.text
    over = c.post("/auth/device", json={"device_id": "flood-device-id-overflow"})
    assert over.status_code == 429, over.text
    print(f"  ok  signup cap holds at {limit}/window for new devices")

    # A returning device still gets in — the cap must never lock out real users.
    returning = c.post("/auth/device", json={"device_id": DEVICE_A})
    assert returning.status_code == 200, returning.text
    print("  ok  returning device unaffected by the cap")

    print("\nDEVICE AUTH TESTS PASSED ✅")
    if os.path.exists("./device_test.db"):
        os.remove("./device_test.db")


if __name__ == "__main__":
    main()
