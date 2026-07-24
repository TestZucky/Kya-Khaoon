"""
End-to-end smoke test on SQLite with the fake Swiggy client.

Run:  DATABASE_URL=sqlite:///./smoke.db SWIGGY_CLIENT=fake python -m tests.test_smoke

Exercises the real request path: onboard → build a deck (both recommender stages)
→ swipe. Asserts the guardrails that actually matter — allergy exclusion, ad
de-prioritisation, and side-dish rejection.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./smoke.db")
os.environ.setdefault("SWIGGY_CLIENT", "fake")

from fastapi.testclient import TestClient  # noqa: E402

from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402


def main() -> None:
    init_db()
    seed()
    client = TestClient(app)

    assert client.get("/health").json() == {"status": "ok"}

    # Log in via SMS OTP, then onboard: a vegetarian user, allergic to dairy.
    from tests.helpers import login

    headers = login(client, "9876543210")
    onboard = client.post(
        "/onboard",
        headers=headers,
        json={
            "swiggy_address_id": "228077662",
            "profile": {
                "diet": "veg",
                "allergies": ["dairy"],
                "goal": "healthier",
                "budget_band": "under_200",
                "cuisines": ["Chinese", "South Indian"],
            },
        },
    ).json()
    print("onboarded user", onboard["id"])

    deck = client.post(
        "/decks",
        headers=headers,
        json={"mood": "light", "hunger": "normal"},
    ).json()
    cards = deck["cards"]
    print(f"deck {deck['deck_id']} → {len(cards)} cards")
    for c in cards:
        flag = " [AD]" if c["is_ad"] else ""
        print(f"  · {c['name']:<26} ₹{c['price']:<4} {c['restaurant']:<22}{flag}  — {c['reason']}")

    # Guardrails.
    assert cards, "deck came back empty"
    assert all(c["is_veg"] for c in cards), "non-veg card served to a veg user"
    assert all("dairy" not in c["allergens"] for c in cards), "dairy served to a dairy allergy!"
    assert not any(c["name"].lower().endswith("rice") for c in cards), "side dish leaked in"
    assert not any(c["is_ad"] for c in cards), "an ad won the top offer"

    swipe = client.post(
        "/swipes",
        headers=headers,
        json={"card_id": cards[0]["card_id"], "direction": "right"},
    )
    assert swipe.status_code == 201, swipe.text
    print("swiped right on", cards[0]["name"], "→ swipe", swipe.json()["swipe_id"])

    print("\nALL SMOKE CHECKS PASSED ✅")


if __name__ == "__main__":
    main()
