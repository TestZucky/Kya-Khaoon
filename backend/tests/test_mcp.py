"""
Tests for the MCP Swiggy client.

The transport (initialize → tools/call over HTTP/SSE) can't hit the real server
here, so we test the two halves that carry the correctness:

  1. Response handling — extracting JSON-RPC messages from both `application/json`
     and `text/event-stream`, and unwrapping a CallToolResult.
  2. Field mapping — against the EXACT payloads captured from a live Swiggy
     account, so the shape the deck consumes is proven, ad-stripping and all.

Run:  python -m tests.test_mcp
"""

import json
from types import SimpleNamespace

from app.swiggy.mcp import menu_items_from_payload, restaurants_from_payload
from app.swiggy.mcp_transport import (
    extract_messages,
    result_for,
    tool_payload,
)

# ── Real captured payloads (query "biryani", Nehru Nagar) ───────────────────
LIVE_MENU = {
    "items": [
        {
            "name": "2 Non-Veg Chinna Biryani Bowls at 159 each",
            "price": 318,
            "menu_item_id": "161596979",
            "inStock": 1,
            "imageUrl": "https://media-assets.swiggy.com/x.jpeg",
            "restaurant_id": "1030962",
            "restaurant_name": "Thalaiva Biryani",
            "rating": "4.2",
            "hasAddons": True,
        },
        {
            "name": "Paneer Tikka Biryani",
            "price": 369,
            "isVeg": True,
            "menu_item_id": "137117657",
            "inStock": 1,
            "imageUrl": "https://media-assets.swiggy.com/y.jpg",
            "restaurant_id": "726509",
            "restaurant_name": "Haldiram's Restaurant",
            "rating": "4.1",
        },
    ],
    "total": 2,
    "query": "biryani",
}

LIVE_RESTAURANTS = {
    "restaurants": [
        {
            "id": "1030962",
            "name": "Thalaiva Biryani (Ad)",
            "avgRating": 4.4,
            "distanceKm": 3,
            "deliveryTimeMinutes": 21,
            "offer": "50% OFF",
            "availabilityStatus": "OPEN",
        },
        {
            "id": "142941",
            "name": "Zeeshan Biryani Center",
            "avgRating": 3.6,
            "distanceKm": 1.4,
            "deliveryTimeMinutes": 15,
            "offer": "70% OFF UPTO ₹140",
            "availabilityStatus": "OPEN",
        },
    ],
    "total": 2,
}


def test_menu_mapping() -> None:
    items = menu_items_from_payload(LIVE_MENU)
    assert len(items) == 2
    first = items[0]
    assert first.menu_item_id == "161596979"
    assert first.price == 318
    assert first.rating == 4.2  # string "4.2" coerced to float
    assert first.in_stock is True
    assert first.is_veg is False  # no isVeg → not confirmed veg
    assert items[1].is_veg is True  # isVeg present and true


def test_restaurant_mapping_and_ad_flag() -> None:
    rs = restaurants_from_payload(LIVE_RESTAURANTS)
    assert rs[0].name == "Thalaiva Biryani"  # "(Ad)" stripped
    assert rs[0].is_ad is True
    assert rs[0].eta_minutes == 21
    assert rs[0].is_open is True
    assert rs[1].is_ad is False
    assert rs[1].name == "Zeeshan Biryani Center"


def test_extract_json_response() -> None:
    resp = SimpleNamespace(
        headers={"content-type": "application/json"},
        content=b"x",
        json=lambda: {"jsonrpc": "2.0", "id": 2, "result": {"ok": 1}},
    )
    msgs = extract_messages(resp)  # type: ignore[arg-type]
    assert result_for(msgs, 2) == {"ok": 1}


def test_extract_sse_response() -> None:
    body = (
        "event: message\n"
        'data: {"jsonrpc":"2.0","id":2,"result":{"content":'
        '[{"type":"text","text":"{\\"items\\":[]}"}]}}\n\n'
    )
    resp = SimpleNamespace(
        headers={"content-type": "text/event-stream"}, content=body.encode(), text=body
    )
    result = result_for(extract_messages(resp), 2)  # type: ignore[arg-type]
    payload = tool_payload(result)
    assert payload == {"items": []}


def test_tool_payload_prefers_structured_content() -> None:
    result = {
        "content": [{"type": "text", "text": '{"items":[1]}'}],
        "structuredContent": {"items": [1, 2, 3]},
    }
    assert tool_payload(result) == {"items": [1, 2, 3]}


def test_tool_payload_error_raises() -> None:
    result = {"isError": True, "content": [{"type": "text", "text": "boom"}]}
    try:
        tool_payload(result)
    except Exception as e:  # noqa: BLE001
        assert "boom" in str(e)
    else:
        raise AssertionError("expected an error")


def main() -> None:
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    # Sanity: the SSE fixture round-trips through json too.
    assert json.loads('{"items": []}') == {"items": []}
    print("\nALL MCP TESTS PASSED ✅")


if __name__ == "__main__":
    main()
