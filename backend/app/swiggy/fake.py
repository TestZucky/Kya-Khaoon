"""
Deterministic Swiggy stand-in for local dev and tests. No network.

Returns plausible results shaped like the real API — including the annoying bits
we must handle: an "(Ad)" restaurant, a side-dish false positive, and items with
no veg flag. Same query → same output, so tests can assert on it.
"""

from app.swiggy.client import Address, CartTotal, MenuItem, PastOrder, RestaurantInfo

# Swiggy's own charges, as flat dev stand-ins. Real values come from the live cart.
_GST_RATE = 0.05
_DELIVERY_FEE = 35
_PACKING_FEE = 20
_PLATFORM_FEE = 10


def _seed(query: str) -> int:
    return sum(ord(c) for c in query.lower())


def _price_for_item_id(menu_item_id: str) -> int:
    """
    Recover the price `search_menu` invented for this id, so the fake cart total
    builds on the exact price the card showed. Ids are f"{seed}{nn}" — mirror the
    per-row pricing there. Unknown shapes fall back to the base price.
    """
    try:
        seed, suffix = int(menu_item_id[:-2]), menu_item_id[-2:]
    except (ValueError, IndexError):
        return 0
    base = 180 + seed % 220
    return {"01": base, "02": base + 120, "03": 140, "04": base + 40}.get(suffix, base)


# Plausible stand-in addresses for dev — never a real person's data.
FAKE_ADDRESSES = [
    Address(id="addr-home", label="Home", line="Nehru Nagar, Bhilai, Chhattisgarh"),
    Address(id="addr-work", label="Work", line="DDU Nagar, Raipur, Chhattisgarh"),
]


class FakeSwiggyClient:
    def __init__(self) -> None:
        # Records adds so tests can assert without a real Swiggy account.
        self.cart: list[dict] = []

    async def get_addresses(self, *, user_token: str | None = None) -> list[Address]:
        return list(FAKE_ADDRESSES)

    async def get_cart(self, *, user_token: str | None = None) -> CartTotal | None:
        if not self.cart:
            return None
        item_total = sum(
            _price_for_item_id(e["menu_item_id"]) * e["quantity"] for e in self.cart
        )
        taxes = round(item_total * _GST_RATE)
        total = item_total + taxes + _DELIVERY_FEE + _PACKING_FEE + _PLATFORM_FEE
        return CartTotal(
            total=total,
            item_total=item_total,
            taxes=taxes,
            delivery_fee=_DELIVERY_FEE,
            packing_fee=_PACKING_FEE,
            platform_fee=_PLATFORM_FEE,
            discount=None,
        )

    async def get_orders(
        self, *, address_id: str = "", limit: int = 20, user_token: str | None = None
    ) -> list[PastOrder]:
        # A deterministic history with a clear pattern for the recommender to find:
        # a biryani/North-Indian lean around a ~₹300 spend, plus some variety.
        orders = [
            PastOrder("Chicken Biryani", "Paradise Biryani", "North Indian", 320, 2),
            PastOrder("Butter Chicken", "Punjabi Dhaba", "North Indian", 340, 5),
            PastOrder("Chicken Biryani", "Behrouz Biryani", "North Indian", 360, 9),
            PastOrder("Masala Dosa", "Sagar Ratna", "South Indian", 180, 12),
            PastOrder("Paneer Tikka", "Punjabi Dhaba", "North Indian", 280, 16),
            PastOrder("Veg Hakka Noodles", "Wok Express", "Chinese", 240, 21),
            PastOrder("Chicken Biryani", "Paradise Biryani", "North Indian", 320, 27),
        ]
        return orders[:limit]

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
        self.cart.append(
            {
                "restaurant_id": restaurant_id,
                "menu_item_id": menu_item_id,
                "quantity": quantity,
            }
        )

    async def search_menu(
        self,
        *,
        address_id: str,
        query: str,
        veg_only: bool = False,
        user_token: str | None = None,
    ) -> list[MenuItem]:
        s = _seed(query)
        base = 180 + s % 220
        rows = [
            MenuItem(
                menu_item_id=f"{s}01",
                name=f"{query.title()} Special",
                price=base,
                restaurant_id=f"r{s % 97}",
                restaurant_name=f"{query.title()} House",
                rating=4.2,
                image_url=None,
                in_stock=True,
                is_veg=veg_only,
            ),
            MenuItem(
                menu_item_id=f"{s}02",
                name=f"Premium {query.title()}",
                price=base + 120,
                restaurant_id=f"r{(s + 5) % 97}",
                restaurant_name=f"The {query.title()} Life (Ad)",
                rating=4.4,
                image_url=None,
                in_stock=True,
                is_veg=veg_only,
            ),
            # A side-dish false positive stage 2 must reject.
            MenuItem(
                menu_item_id=f"{s}03",
                name="Steamed Rice",
                price=140,
                restaurant_id=f"r{(s + 9) % 97}",
                restaurant_name="Budget Kitchen",
                rating=3.3,
                image_url=None,
                in_stock=True,
                is_veg=True,
            ),
            # Out of stock — must be filtered out.
            MenuItem(
                menu_item_id=f"{s}04",
                name=f"{query.title()} Combo",
                price=base + 40,
                restaurant_id=f"r{(s + 12) % 97}",
                restaurant_name="Sold Out Diner",
                rating=4.0,
                image_url=None,
                in_stock=False,
                is_veg=veg_only,
            ),
        ]
        return [r for r in rows if not veg_only or r.is_veg]

    async def search_restaurants(
        self,
        *,
        address_id: str,
        query: str,
        user_token: str | None = None,
    ) -> list[RestaurantInfo]:
        s = _seed(query)
        return [
            RestaurantInfo(
                restaurant_id=f"r{s % 97}",
                name=f"{query.title()} House",
                rating=4.2,
                eta_minutes=22,
                distance_km=1.4,
                is_open=True,
                is_ad=False,
                offer="50% OFF",
            ),
            RestaurantInfo(
                restaurant_id=f"r{(s + 5) % 97}",
                name=f"The {query.title()} Life (Ad)",
                rating=4.4,
                eta_minutes=21,
                distance_km=3.0,
                is_open=True,
                is_ad=True,
                offer="50% OFF",
            ),
            RestaurantInfo(
                restaurant_id=f"r{(s + 9) % 97}",
                name="Budget Kitchen",
                rating=3.3,
                eta_minutes=14,
                distance_km=1.4,
                is_open=True,
                is_ad=False,
                offer=None,
            ),
            RestaurantInfo(
                restaurant_id=f"r{(s + 12) % 97}",
                name="Sold Out Diner",
                rating=4.0,
                eta_minutes=30,
                distance_km=5.0,
                is_open=False,
                is_ad=False,
                offer=None,
            ),
        ]
