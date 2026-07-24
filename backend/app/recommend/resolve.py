"""
Stage 2 — turn one dish concept into the best live Swiggy offer.

Searches the menu for the concept's query, then ranks the in-stock hits. Each
menu item already carries everything a card needs — restaurant name, price,
rating, photo — so the menu search alone is the source of truth.

We also fire a restaurant search, but only as *optional enrichment*: when its
ids happen to line up with the menu items we borrow the ETA / offer / ad flag.
Swiggy's two searches often live in different id spaces (menu items keyed by
one id, the restaurant search by another), so a missing match means "no extra
detail", NOT "drop this dish" — the item is already known to be orderable.

Filtering:
  · drop out-of-stock items
  · drop side dishes / combos that match the word but aren't the meal
  · drop only when a restaurant DID match and reported itself closed
  · de-prioritise "(Ad)" placements so a sponsored slot never wins on its own
    (a sponsored slot must never be presented as the personalized best fit)
  · for veg diets, ask Swiggy for veg-only rather than trusting the absent flag

Returns None only when nothing usable is in stock — the caller drops that card.
"""

from dataclasses import dataclass

from app.swiggy.client import MenuItem, RestaurantInfo, SwiggyClient

# Markers of an add-on/combo listing rather than a real dish.
_SIDE_MARKERS = ("combo", "bowls at", "add on", "add-on", "extra ")
# Plain staples that, when they ARE the whole short name, mean a side —
# "Steamed Rice" / "Biryani Rice" (side) but not "Chicken Fried Rice" (a meal).
_SIDE_STAPLES = {"rice", "roti", "naan", "raita", "curd", "gravy", "papad"}


@dataclass
class ResolvedOffer:
    menu_item_id: str
    restaurant_id: str
    restaurant_name: str
    price: int
    eta_minutes: int | None
    rating: float | None
    image_url: str | None
    is_ad: bool
    offer: str | None


def _looks_like_side(name: str) -> bool:
    low = name.lower().strip()
    if any(m in low for m in _SIDE_MARKERS):
        return True
    words = low.split()
    return len(words) <= 2 and bool(words) and words[-1] in _SIDE_STAPLES


async def resolve_offer(
    client: SwiggyClient,
    *,
    address_id: str,
    query: str,
    veg_only: bool,
    budget_ceiling: int,
    user_token: str | None = None,
) -> ResolvedOffer | None:
    items = await client.search_menu(
        address_id=address_id, query=query, veg_only=veg_only, user_token=user_token
    )
    restaurants = await client.search_restaurants(
        address_id=address_id, query=query, user_token=user_token
    )
    by_id = {r.restaurant_id: r for r in restaurants}

    candidates: list[tuple[float, MenuItem, RestaurantInfo | None]] = []
    for item in items:
        if not item.in_stock or _looks_like_side(item.name):
            continue
        # Optional enrichment. Usually None (the two searches don't share ids);
        # only drop the item when a restaurant matched AND said it's closed.
        rest = by_id.get(item.restaurant_id)
        if rest is not None and not rest.is_open:
            continue
        candidates.append((_rank(item, rest, budget_ceiling), item, rest))

    if not candidates:
        return None

    candidates.sort(key=lambda c: c[0], reverse=True)
    _, item, rest = candidates[0]
    return ResolvedOffer(
        menu_item_id=item.menu_item_id,
        restaurant_id=item.restaurant_id,
        restaurant_name=rest.name if rest else item.restaurant_name,
        price=item.price,
        eta_minutes=rest.eta_minutes if rest else None,
        rating=(rest.rating if rest else None) or item.rating,
        image_url=item.image_url,
        is_ad=rest.is_ad if rest else False,
        offer=rest.offer if rest else None,
    )


def _rank(item: MenuItem, rest: RestaurantInfo | None, ceiling: int) -> float:
    score = 0.0
    rating = (rest.rating if rest else None) or item.rating or 3.5
    score += rating * 2  # quality
    if item.price <= ceiling:
        score += 3
    else:
        score -= (item.price - ceiling) / 50  # gentle over-budget penalty
    if rest and rest.eta_minutes is not None:
        score += max(0, (40 - rest.eta_minutes) / 10)  # faster is better
    if rest and rest.is_ad:
        score -= 4  # a sponsored slot must earn its place on merit, not placement
    return score
