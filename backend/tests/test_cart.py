"""
Tests for the "Order on Swiggy" cart hand-off.

Part A (fake): the whole path onboard → deck → cart returns a clean CartOut.
Part B (mcp mock): the real client calls `update_food_cart` with the resolved
item, forwards the user's token, and — critically — NEVER calls a
place-order / confirm tool. Kya Khaoon builds the cart, Swiggy takes payment.

Run:  python -m tests.test_cart

One DB and one app instance for the whole run (the engine binds at import, so a
mid-run DB switch would strand writes on the old file); parts differ only by which
Swiggy client is active, toggled via SWIGGY_CLIENT + a settings-cache clear.
"""

import os
import threading
from http.server import HTTPServer

DB_URL = "sqlite:///./cart_test.db"
os.environ["DATABASE_URL"] = DB_URL
os.environ.setdefault("SWIGGY_CLIENT", "fake")

from app.config import get_settings  # noqa: E402
from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def _use(client_kind: str, mcp_url: str = "") -> None:
    os.environ["SWIGGY_CLIENT"] = client_kind
    os.environ["SWIGGY_MCP_URL"] = mcp_url
    get_settings.cache_clear()


def part_a_fake(c: TestClient) -> None:
    from tests.helpers import login

    _use("fake")
    h = login(c, "9333300001")
    c.post(
        "/onboard",
        headers=h,
        json={
            "swiggy_address_id": "228077662",
            "profile": {"diet": "non_veg", "budget_band": "above_500"},
        },
    )
    deck = c.post("/decks", headers=h, json={"mood": "comfort"}).json()
    card = deck["cards"][0]

    r = c.post("/cart", headers=h, json={"card_id": card["card_id"]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["item"] == card["name"] and body["price"] == card["price"]
    assert body["checkout_url"].startswith("https://www.swiggy.com")
    print(f"  ok  fake: /cart → added {body['item']} @ {body['restaurant']}")


def part_b_mcp_mock(c: TestClient) -> None:
    from tests.test_mcp_integration import Handler, seen_auth, seen_tools

    seen_tools.clear()
    seen_auth.clear()
    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    _use("mcp", f"http://127.0.0.1:{port}")
    from tests.helpers import login

    h = login(c, "9333300002")
    c.post(
        "/onboard",
        headers=h,
        json={
            "swiggy_address_id": "228077662",
            "swiggy_token": "tok-cart-user",
            "profile": {"diet": "non_veg", "budget_band": "above_500"},
        },
    )
    deck = c.post("/decks", headers=h, json={"mood": "comfort"}).json()
    card = deck["cards"][0]

    r = c.post("/cart", headers=h, json={"card_id": card["card_id"]})
    server.shutdown()
    assert r.status_code == 200, r.text

    tool_names = [name for name, _ in seen_tools]
    assert "update_food_cart" in tool_names, tool_names
    # The safety line: no order is placed or paid server-side.
    for forbidden in ("place_food_order", "confirm_order", "check_payment_status"):
        assert forbidden not in tool_names, f"{forbidden} must not be called"

    add = next(args for name, args in seen_tools if name == "update_food_cart")
    assert add["cartItems"][0]["menu_item_id"]
    assert add["restaurantId"] and add["addressId"] == "228077662"
    assert all(a == "Bearer tok-cart-user" for a in seen_auth if a is not None)
    print("  ok  mcp: update_food_cart called, no order-placement tool touched")
    print("  ok  mcp: user token forwarded to cart call")


def main() -> None:
    init_db()
    seed()
    c = TestClient(app)
    try:
        part_a_fake(c)
        part_b_mcp_mock(c)
        print("\nCART TESTS PASSED ✅")
    finally:
        for f in ("./cart_test.db",):
            if os.path.exists(f):
                os.remove(f)


if __name__ == "__main__":
    main()
