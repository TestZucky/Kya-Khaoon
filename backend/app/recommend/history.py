"""
Mine the user's Swiggy order history for taste patterns, before we build a deck.

Swiggy connection is mandatory before the first deck, so history is available for
most users. We distill it into two cheap signals:

  * a compact `summary` string injected into the stage-1 LLM prompt (favourite
    dishes / cuisines, typical spend, what they just ordered), and
  * `recent` — dish names ordered in the last week, so the deck offers variety
    rather than what they ate on Tuesday.

Best-effort throughout: no history (or a fetch failure upstream) just means an
empty summary and the recommender behaves exactly as before.
"""

from collections import Counter
from dataclasses import dataclass

from app.swiggy.client import PastOrder

_RECENT_DAYS = 7


@dataclass
class OrderInsights:
    summary: str | None  # one line for the LLM prompt, or None when no history
    recent: list[str]  # dish names ordered in the last week (variety signal)


def summarize_orders(orders: list[PastOrder]) -> OrderInsights:
    if not orders:
        return OrderInsights(summary=None, recent=[])

    dish_counts = Counter(o.item_name for o in orders if o.item_name)
    cuisine_counts = Counter(o.cuisine for o in orders if o.cuisine)
    prices = [o.price for o in orders if o.price]
    recent = list(
        dict.fromkeys(
            o.item_name
            for o in orders
            if o.item_name and o.days_ago is not None and o.days_ago <= _RECENT_DAYS
        )
    )

    parts: list[str] = []

    top_dishes = [
        f"{name} (x{n})" if n > 1 else name
        for name, n in dish_counts.most_common(3)
    ]
    if top_dishes:
        parts.append(f"often orders {', '.join(top_dishes)}")

    top_cuisines = [name for name, _ in cuisine_counts.most_common(2)]
    if top_cuisines:
        parts.append(f"leans {', '.join(top_cuisines)}")

    if prices:
        typical = round(sum(prices) / len(prices) / 10) * 10
        parts.append(f"usual spend ~₹{typical}")

    if recent:
        parts.append(f"just ordered {', '.join(recent[:4])} (avoid repeats)")

    summary = "; ".join(parts) if parts else None
    return OrderInsights(summary=summary, recent=recent)
