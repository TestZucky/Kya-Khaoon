"""
Integration test for the MCP transport over a real socket.

Stands up a minimal mock MCP server that speaks the Streamable HTTP protocol
(initialize → initialized → tools/call), points the REAL McpSwiggyClient at it,
and asserts the full round-trip: the handshake completes, the user's bearer token
is forwarded, and Swiggy-shaped responses map to our dataclasses.

This exercises everything except the real Swiggy server itself.

Run:  SWIGGY_CLIENT=mcp SWIGGY_MCP_URL=placeholder python -m tests.test_mcp_integration
"""

import asyncio
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# Captured so tests can assert the token was forwarded and which tools were called.
seen_auth: list[str | None] = []
seen_tools: list[tuple[str, dict]] = []

MENU = {
    "items": [
        {
            "name": "Chicken Biryani",
            "price": 219,
            "menu_item_id": "87630555",
            "inStock": 1,
            "imageUrl": "https://img/x.jpg",
            "restaurant_id": "508690",
            "restaurant_name": "Taimur Biryani Centre",
            "rating": "3.6",
        },
        {
            "name": "Paneer Tikka Biryani",
            "price": 369,
            "isVeg": True,
            "menu_item_id": "137117657",
            "inStock": 1,
            "imageUrl": "https://img/y.jpg",
            "restaurant_id": "726509",
            "restaurant_name": "Haldiram's Restaurant",
            "rating": "4.1",
        },
    ]
}

ORDERS = {
    "orders": [
        {
            "restaurant_name": "Paradise Biryani (Ad)",
            "cuisines": ["North Indian", "Biryani"],
            "order_time": "2026-07-22T20:14:00Z",
            "items": [{"name": "Chicken Biryani", "price": 320}],
        },
        {
            "restaurant_name": "Sagar Ratna",
            "cuisine": "South Indian",
            "orderTime": "2026-07-18T09:02:00Z",
            "order_items": [{"item_name": "Masala Dosa", "final_price": 180}],
        },
    ]
}

RESTAURANTS = {
    "restaurants": [
        {
            "id": "508690",
            "name": "Taimur Biryani Centre",
            "avgRating": 3.7,
            "distanceKm": 1.4,
            "deliveryTimeMinutes": 18,
            "offer": "70% OFF",
            "availabilityStatus": "OPEN",
        },
        {
            "id": "726509",
            "name": "Haldiram's Restaurant (Ad)",
            "avgRating": 4.1,
            "distanceKm": 3,
            "deliveryTimeMinutes": 22,
            "availabilityStatus": "OPEN",
        },
    ]
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # silence
        pass

    def do_POST(self):
        seen_auth.append(self.headers.get("Authorization"))
        length = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(length) or b"{}")
        method = req.get("method")

        if method == "notifications/initialized":
            self.send_response(202)
            self.end_headers()
            return

        if method == "initialize":
            result = {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "serverInfo": {"name": "mock", "version": "1"},
            }
            self._json(req["id"], result, session="mock-session")
            return

        if method == "tools/call":
            name = req["params"]["name"]
            seen_tools.append((name, req["params"].get("arguments", {})))
            args = req["params"].get("arguments", {})
            if name == "search_menu":
                payload: dict = MENU
            elif name == "search_restaurants":
                payload = RESTAURANTS
            elif name == "get_food_orders":
                # Mirror the real server: history is scoped to an address, and the
                # call is rejected outright without one.
                if not args.get("addressId"):
                    result = {
                        "content": [
                            {
                                "type": "text",
                                "text": "addressId is required. Call get_addresses "
                                "first to retrieve the user's saved addresses, then "
                                "pass the selected addressId to this tool.",
                            }
                        ],
                        "isError": True,
                    }
                    self._json(req["id"], result)
                    return
                payload = ORDERS
            else:  # update_food_cart / anything else → generic success
                payload = {"cart": {"items": 1}}
            result = {
                "content": [{"type": "text", "text": json.dumps(payload)}],
                "isError": False,
            }
            self._json(req["id"], result)
            return

        self._json(req.get("id"), None)

    def _json(self, req_id, result, session=None):
        body = json.dumps({"jsonrpc": "2.0", "id": req_id, "result": result}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        if session:
            self.send_header("Mcp-Session-Id", session)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()

    # Point the real client at the mock and force a rebuild of cached settings.
    os.environ["SWIGGY_CLIENT"] = "mcp"
    os.environ["SWIGGY_MCP_URL"] = f"http://127.0.0.1:{port}"
    from app.config import get_settings

    get_settings.cache_clear()
    from app.swiggy.mcp import McpSwiggyClient

    client = McpSwiggyClient()

    async def run():
        menu = await client.search_menu(
            address_id="228077662", query="biryani", user_token="user-abc-123"
        )
        rests = await client.search_restaurants(
            address_id="228077662", query="biryani", user_token="user-abc-123"
        )
        orders = await client.get_orders(
            address_id="228077662", limit=20, user_token="user-abc-123"
        )
        return menu, rests, orders

    menu, rests, orders = asyncio.run(run())
    server.shutdown()

    # Transport round-tripped and mapped.
    assert len(menu) == 2, menu
    assert menu[0].name == "Chicken Biryani" and menu[0].price == 219
    assert menu[0].is_veg is False and menu[1].is_veg is True
    print(f"  ok  search_menu → {[m.name for m in menu]}")

    assert rests[1].name == "Haldiram's Restaurant"  # "(Ad)" stripped
    assert rests[1].is_ad is True and rests[0].is_ad is False
    assert rests[0].eta_minutes == 18 and rests[0].is_open is True
    print(f"  ok  search_restaurants → ad-stripped, eta parsed")

    # Order history: the tool REQUIRES addressId. Omitting it doesn't degrade the
    # response, it fails the call — and the failure is swallowed as best-effort in
    # build_deck, so stage 1 silently loses its taste patterns. Assert the argument
    # is actually sent, not just that the mapping works.
    history_args = [a for name, a in seen_tools if name == "get_food_orders"]
    assert history_args, seen_tools
    assert all(a.get("addressId") == "228077662" for a in history_args), history_args
    print(f"  ok  get_food_orders sent addressId on all {len(history_args)} calls")

    assert len(orders) == 2, orders
    assert orders[0].item_name == "Chicken Biryani" and orders[0].price == 320
    assert orders[0].restaurant_name == "Paradise Biryani"  # "(Ad)" stripped
    assert orders[0].cuisine == "North Indian, Biryani"  # list joined
    # Alternate field spellings (orderTime / item_name / final_price) map too.
    assert orders[1].item_name == "Masala Dosa" and orders[1].price == 180
    assert orders[0].days_ago is not None and orders[0].days_ago >= 0
    print(f"  ok  get_food_orders → {[o.item_name for o in orders]}")

    # The user's bearer token was forwarded on every request.
    assert seen_auth and all(a == "Bearer user-abc-123" for a in seen_auth), seen_auth
    print(f"  ok  bearer token forwarded on all {len(seen_auth)} requests")

    print("\nMCP TRANSPORT INTEGRATION PASSED ✅")


if __name__ == "__main__":
    main()
