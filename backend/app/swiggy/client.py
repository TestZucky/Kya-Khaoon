"""
The one interface the rest of the backend knows about.

Everything Swiggy — fake or real — implements SwiggyClient. The recommender joins
`search_menu` (dish, price, image, stock) with `search_restaurants` (ETA, open
status, rating, ad flag) on restaurant_id. Fields the live API doesn't provide
(ingredients, allergens, cooking style) never appear here — they live on
DishConcept in our own database.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class MenuItem:
    menu_item_id: str
    name: str
    price: int
    restaurant_id: str
    restaurant_name: str
    rating: float | None
    image_url: str | None
    in_stock: bool
    is_veg: bool  # False can mean non-veg OR unmarked — never trust False as "safe"


@dataclass
class Address:
    id: str
    label: str  # "Home", "Work", …
    line: str  # human-readable address line


@dataclass
class RestaurantInfo:
    restaurant_id: str
    name: str
    rating: float | None
    eta_minutes: int | None
    distance_km: float | None
    is_open: bool
    is_ad: bool  # Swiggy smuggles "(Ad)" into the name; we surface it as a flag
    offer: str | None


@dataclass
class PastOrder:
    """One item the user has ordered before — the raw material for pattern mining."""

    item_name: str
    restaurant_name: str
    cuisine: str | None  # Swiggy doesn't always label it; None when unknown
    price: int | None
    days_ago: int | None  # how long ago, None when the date is unavailable


@dataclass
class CartTotal:
    """
    Swiggy's own cart arithmetic — the *final payable*, which is always ≥ the menu
    price we show on a card. The menu price covers one dish; this adds the charges
    only Swiggy can compute (tax, delivery, packing, platform fee) and subtracts
    whatever offer actually applied. Every component is optional because Swiggy
    doesn't always itemise; `total` is the number worth showing the user.
    """

    total: int  # final payable in rupees
    item_total: int | None = None
    taxes: int | None = None
    delivery_fee: int | None = None
    packing_fee: int | None = None
    platform_fee: int | None = None
    discount: int | None = None  # positive number = amount taken off


class SwiggyClient(Protocol):
    async def get_addresses(
        self, *, user_token: str | None = None
    ) -> list[Address]:
        """The user's saved Swiggy delivery addresses (location for search/cart)."""
        ...

    async def search_menu(
        self,
        *,
        address_id: str,
        query: str,
        veg_only: bool = False,
        user_token: str | None = None,
    ) -> list[MenuItem]: ...

    async def search_restaurants(
        self,
        *,
        address_id: str,
        query: str,
        user_token: str | None = None,
    ) -> list[RestaurantInfo]: ...

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
        """
        Add one dish to the user's Swiggy cart. This is the hand-off — it builds
        the cart, it does NOT place or pay for the order. Raises on failure.
        """
        ...

    async def get_orders(
        self, *, address_id: str, limit: int = 20, user_token: str | None = None
    ) -> list[PastOrder]:
        """
        The user's recent past orders, newest first — mined for taste patterns
        before we build a deck. Best-effort: returns [] when history is
        unavailable rather than blocking recommendations.

        `address_id` is required — Swiggy scopes history to a delivery address and
        rejects the call without one.
        """
        ...

    async def get_cart(
        self, *, address_id: str, user_token: str | None = None
    ) -> CartTotal | None:
        """
        The live Swiggy cart's real payable total, read straight after we add an
        item. None when Swiggy can't tell us — the caller then falls back to
        showing the menu price rather than inventing a number.

        `address_id` is required — delivery charges depend on where it's going,
        and Swiggy rejects the call without one.
        """
        ...
