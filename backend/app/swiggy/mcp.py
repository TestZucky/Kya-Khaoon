"""
Real Swiggy client, backed by the remote Swiggy MCP server.

Each user OAuths that one server and the backend forwards their bearer token per
call (a static token can stand in for single-account testing). This maps our two
methods onto the `search_menu` / `search_restaurants` tools whose live responses
we verified against a real account, turning the "(Ad)" name suffix into an
`is_ad` flag and treating a missing `isVeg` as "not confirmed veg" (never "safe").

The mapping is pure functions so it can be tested against captured payloads; the
MCP round-trip lives in `mcp_transport.py`.
"""

from app.config import get_settings
from app.swiggy.client import Address, CartTotal, MenuItem, PastOrder, RestaurantInfo
from app.swiggy.mcp_transport import StreamableHttpMcp

_AD = "(Ad)"


def _clean(name: str) -> tuple[str, bool]:
    is_ad = _AD in name
    return name.replace(_AD, "").strip(), is_ad


def _as_float(v: object) -> float | None:
    try:
        return float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _as_int(v: object) -> int | None:
    try:
        return int(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def menu_items_from_payload(data: dict) -> list[MenuItem]:
    items: list[MenuItem] = []
    for it in data.get("items", []):
        name, _ = _clean(str(it.get("restaurant_name", "")))
        items.append(
            MenuItem(
                menu_item_id=str(it["menu_item_id"]),
                name=str(it.get("name", "")),
                price=int(it.get("price", 0)),
                restaurant_id=str(it.get("restaurant_id", "")),
                restaurant_name=name,
                rating=_as_float(it.get("rating")),
                image_url=it.get("imageUrl"),
                in_stock=bool(it.get("inStock", 1)),
                # isVeg is present only when true; its absence is unknown, NOT
                # "non-veg" — so False here means "not confirmed veg".
                is_veg=bool(it.get("isVeg", False)),
            )
        )
    return items


def addresses_from_payload(data: dict) -> list[Address]:
    out: list[Address] = []
    for a in data.get("addresses", []):
        out.append(
            Address(
                id=str(a.get("id", "")),
                label=str(a.get("addressTag") or a.get("addressCategory") or "Saved"),
                line=str(a.get("addressLine", "")),
            )
        )
    return out


def _first_int(d: dict, *keys: str) -> int | None:
    """First of `keys` present in `d` that parses as an int (rupees)."""
    for k in keys:
        if k in d:
            v = _as_int(d[k])
            if v is not None:
                return v
    return None


def cart_total_from_payload(data: dict) -> CartTotal | None:
    """
    Swiggy's cart bill → CartTotal. Field names vary across responses, so each
    component tries a few aliases and stays None when absent. Without a payable
    total there's nothing trustworthy to show, so we return None rather than
    guessing a number the user would be charged against.
    """
    bill = data.get("cart") or data.get("bill") or data.get("data") or data
    if not isinstance(bill, dict):
        return None

    total = _first_int(
        bill, "total", "grandTotal", "grand_total", "finalPrice", "payable", "toPay"
    )
    if total is None:
        return None

    return CartTotal(
        total=total,
        item_total=_first_int(bill, "itemTotal", "item_total", "subTotal", "subtotal"),
        taxes=_first_int(bill, "taxes", "tax", "gst", "totalTax"),
        delivery_fee=_first_int(bill, "deliveryFee", "delivery_fee", "deliveryCharge"),
        packing_fee=_first_int(bill, "packingFee", "packing_charge", "packagingCharge"),
        platform_fee=_first_int(bill, "platformFee", "platform_fee"),
        discount=_first_int(bill, "discount", "totalDiscount", "offerDiscount"),
    )


def _days_ago(value: object) -> int | None:
    """Epoch seconds/millis or an ISO string → whole days ago; None if unparseable."""
    from datetime import datetime, timezone

    if value is None:
        return None
    dt: datetime | None = None
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e12:  # milliseconds
            ts /= 1000.0
        try:
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    elif isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    if dt is None:
        return None
    return max(0, (datetime.now(timezone.utc) - dt).days)


def past_orders_from_payload(data: dict) -> list[PastOrder]:
    """
    Flatten Swiggy's order history into per-item PastOrders. Defensive about field
    names — the live shape varies and history is a best-effort signal, not safety.
    """
    out: list[PastOrder] = []
    for o in data.get("orders", data.get("data", [])) or []:
        if not isinstance(o, dict):
            continue
        rest, _ = _clean(str(o.get("restaurant_name") or o.get("restaurantName") or ""))
        cuisine = o.get("cuisine") or o.get("cuisines")
        if isinstance(cuisine, list):
            cuisine = ", ".join(str(c) for c in cuisine) or None
        when = _days_ago(
            o.get("order_time") or o.get("orderTime") or o.get("ordered_at")
        )
        items = o.get("items") or o.get("order_items") or []
        if not items and o.get("item_name"):  # already per-item
            items = [o]
        for it in items:
            if not isinstance(it, dict):
                continue
            name = str(it.get("name") or it.get("item_name") or "").strip()
            if not name:
                continue
            out.append(
                PastOrder(
                    item_name=name,
                    restaurant_name=rest,
                    cuisine=str(cuisine) if cuisine else None,
                    price=_as_int(it.get("price") or it.get("final_price")),
                    days_ago=when,
                )
            )
    return out


def restaurants_from_payload(data: dict) -> list[RestaurantInfo]:
    out: list[RestaurantInfo] = []
    for r in data.get("restaurants", []):
        name, is_ad = _clean(str(r.get("name", "")))
        out.append(
            RestaurantInfo(
                restaurant_id=str(r.get("id", "")),
                name=name,
                rating=_as_float(r.get("avgRating")),
                eta_minutes=_as_int(r.get("deliveryTimeMinutes")),
                distance_km=_as_float(r.get("distanceKm")),
                is_open=r.get("availabilityStatus") == "OPEN",
                is_ad=is_ad,
                offer=r.get("offer"),
            )
        )
    return out


class McpSwiggyClient:
    def __init__(self) -> None:
        s = get_settings()
        if not s.swiggy_mcp_url:
            raise RuntimeError("SWIGGY_CLIENT=mcp requires SWIGGY_MCP_URL")
        self._url = s.swiggy_mcp_url
        self._timeout = s.swiggy_mcp_timeout
        self._static_token = s.swiggy_mcp_static_token or None

    def _session(self, user_token: str | None) -> StreamableHttpMcp:
        # The user's own token wins; the static token is the testing fallback.
        return StreamableHttpMcp(
            self._url, self._timeout, token=user_token or self._static_token
        )

    async def get_addresses(self, *, user_token: str | None = None) -> list[Address]:
        data = await self._session(user_token).call_tool("get_addresses", {})
        return addresses_from_payload(data)

    async def get_orders(
        self, *, address_id: str, limit: int = 20, user_token: str | None = None
    ) -> list[PastOrder]:
        # addressId is required by the tool, not optional: omitting it fails the
        # call outright rather than returning unscoped history.
        data = await self._session(user_token).call_tool(
            "get_food_orders", {"addressId": address_id, "limit": limit}
        )
        return past_orders_from_payload(data)[:limit]

    async def get_cart(
        self, *, address_id: str, user_token: str | None = None
    ) -> CartTotal | None:
        # addressId is required by the tool: the fees it prices in (delivery
        # especially) are address-dependent, so omitting it fails the call.
        data = await self._session(user_token).call_tool(
            "get_food_cart", {"addressId": address_id}
        )
        return cart_total_from_payload(data)

    async def search_menu(
        self,
        *,
        address_id: str,
        query: str,
        veg_only: bool = False,
        user_token: str | None = None,
    ) -> list[MenuItem]:
        args: dict = {"addressId": address_id, "query": query}
        if veg_only:
            args["vegFilter"] = 1
        data = await self._session(user_token).call_tool("search_menu", args)
        return menu_items_from_payload(data)

    async def search_restaurants(
        self,
        *,
        address_id: str,
        query: str,
        user_token: str | None = None,
    ) -> list[RestaurantInfo]:
        data = await self._session(user_token).call_tool(
            "search_restaurants", {"addressId": address_id, "query": query}
        )
        return restaurants_from_payload(data)

    async def add_to_cart(
        self,
        *,
        address_id: str,
        restaurant_id: str,
        restaurant_name: str,
        menu_item_id: str,
        quantity: int = 1,
        user_token: str | None = None,
    ) -> None:
        # Builds the cart only — never place_food_order. Variants/addons aren't
        # sent yet, so items that require a variant selection are a follow-on.
        await self._session(user_token).call_tool(
            "update_food_cart",
            {
                "restaurantId": restaurant_id,
                "restaurantName": restaurant_name,
                "addressId": address_id,
                "cartItems": [
                    {"menu_item_id": menu_item_id, "quantity": quantity}
                ],
            },
        )
