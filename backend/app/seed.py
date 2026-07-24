"""
Seed the dish-concept catalogue — the decision vocabulary stage 1 chooses from.

Run:  python -m app.seed

These are *concepts*, not listings: "chicken shawarma bowl", not a restaurant's
menu row. Stage 2 finds the live offer. The taxonomy fields (ingredients, cooking
style, allergens, heaviness) are the ones Swiggy can't give us and variety
intelligence needs, so they matter more than they look.
"""

from sqlmodel import Session, select

from app.db import engine, init_db
from app.models import DishConcept

_IMG = "https://images.unsplash.com/{}?w=600&h=750&fit=crop&auto=format"

CONCEPTS: list[dict] = [
    dict(name="Chicken Biryani", search_query="chicken biryani", cuisine="Hyderabadi",
         ingredients=["chicken", "rice", "protein"], cooking_style="rice", is_veg=False,
         allergens=[], heaviness=4, spice_level=3, typical_calories=680, typical_price=280,
         meals=["lunch", "dinner", "late_night"], image_url=_IMG.format("photo-1563379091339-03b21ab4a4f8")),
    dict(name="Paneer Butter Masala", search_query="paneer butter masala", cuisine="North Indian",
         ingredients=["paneer", "dairy", "tomato"], cooking_style="curry", is_veg=True,
         allergens=["dairy"], heaviness=4, spice_level=2, typical_calories=590, typical_price=260,
         meals=["lunch", "dinner"], image_url=_IMG.format("photo-1631452180519-c014fe946bc7")),
    dict(name="Chicken Shawarma Bowl", search_query="chicken shawarma bowl", cuisine="Middle Eastern",
         ingredients=["chicken", "protein", "garlic"], cooking_style="bowl", is_veg=False,
         allergens=[], heaviness=3, spice_level=2, typical_calories=520, typical_price=289,
         meals=["lunch", "snack", "dinner", "late_night"], image_url=_IMG.format("photo-1633945274405-b6c8069047b0")),
    dict(name="Margherita Pizza", search_query="margherita pizza", cuisine="Italian",
         ingredients=["cheese", "dairy", "wheat", "tomato"], cooking_style="baked", is_veg=True,
         allergens=["dairy", "gluten"], heaviness=4, spice_level=1, typical_calories=580, typical_price=299,
         meals=["lunch", "dinner"], image_url=_IMG.format("photo-1650315776778-9a767370950f")),
    dict(name="Veg Hakka Noodles", search_query="veg hakka noodles", cuisine="Chinese",
         ingredients=["wheat", "vegetables", "soy"], cooking_style="noodles", is_veg=True,
         allergens=["gluten", "soy"], heaviness=3, spice_level=2, typical_calories=490, typical_price=200,
         meals=["lunch", "dinner", "late_night"], image_url=_IMG.format("photo-1585032226651-759b368d7246")),
    dict(name="Chicken Thukpa", search_query="chicken thukpa", cuisine="Tibetan",
         ingredients=["chicken", "noodles", "protein"], cooking_style="noodles", is_veg=False,
         allergens=["gluten"], heaviness=2, spice_level=2, typical_calories=430, typical_price=319,
         meals=["lunch", "dinner"], image_url=_IMG.format("photo-1626700051175-6818013e1d4f")),
    dict(name="Masala Dosa", search_query="masala dosa", cuisine="South Indian",
         ingredients=["rice", "potato", "lentil"], cooking_style="fried", is_veg=True,
         allergens=[], heaviness=2, spice_level=2, typical_calories=400, typical_price=150,
         meals=["breakfast", "lunch", "snack"], image_url=_IMG.format("photo-1630383249896-424e482df921")),
    dict(name="Korean Spicy Chicken Noodles", search_query="korean spicy chicken noodles",
         cuisine="Korean", ingredients=["chicken", "noodles", "protein", "soy"], cooking_style="noodles",
         is_veg=False, allergens=["soy", "gluten"], heaviness=3, spice_level=4, typical_calories=560, typical_price=349,
         meals=["lunch", "dinner", "late_night"], image_url=_IMG.format("photo-1668236543090-82eba5ee5976")),
    dict(name="Grilled Chicken Salad", search_query="grilled chicken salad", cuisine="Continental",
         ingredients=["chicken", "protein", "vegetables"], cooking_style="grilled", is_veg=True,
         allergens=[], heaviness=1, spice_level=1, typical_calories=350, typical_price=320,
         meals=["lunch", "dinner"], image_url=_IMG.format("photo-1512621776951-a57141f2eefd")),
    dict(name="Smash Burger", search_query="smash burger", cuisine="American",
         ingredients=["beef", "cheese", "dairy", "wheat"], cooking_style="grilled", is_veg=False,
         allergens=["dairy", "gluten"], heaviness=5, spice_level=1, typical_calories=820, typical_price=350,
         meals=["lunch", "snack", "dinner", "late_night"], image_url=_IMG.format("photo-1550547660-d9450f859349")),
    dict(name="Rajma Chawal", search_query="rajma chawal", cuisine="North Indian",
         ingredients=["kidney beans", "rice", "protein"], cooking_style="rice", is_veg=True,
         allergens=[], heaviness=3, spice_level=2, typical_calories=520, typical_price=180,
         meals=["lunch", "dinner"], image_url=_IMG.format("photo-1603133872878-684f208fb84b")),
    dict(name="Salmon Sushi Set", search_query="salmon sushi", cuisine="Japanese",
         ingredients=["salmon", "fish", "rice", "protein"], cooking_style="bowl", is_veg=False,
         allergens=["fish"], heaviness=2, spice_level=1, typical_calories=380, typical_price=599,
         meals=["lunch", "dinner"], image_url=_IMG.format("photo-1779635593568-e906d1d7e80c")),
    # ── Breakfast ──
    dict(name="Aloo Paratha", search_query="aloo paratha", cuisine="North Indian",
         ingredients=["wheat", "potato", "dairy"], cooking_style="fried", is_veg=True,
         allergens=["gluten", "dairy"], heaviness=3, spice_level=2, typical_calories=450, typical_price=120,
         meals=["breakfast"], image_url=_IMG.format("photo-1626777552726-4a6b54c97e46")),
    dict(name="Poha", search_query="poha", cuisine="North Indian",
         ingredients=["rice", "peanut", "vegetables"], cooking_style="fried", is_veg=True,
         allergens=["peanuts"], heaviness=1, spice_level=1, typical_calories=280, typical_price=90,
         meals=["breakfast"], image_url=_IMG.format("photo-1589301760014-d929f3979dbc")),
    dict(name="Idli Sambar", search_query="idli sambar", cuisine="South Indian",
         ingredients=["rice", "lentil"], cooking_style="steamed", is_veg=True,
         allergens=[], heaviness=1, spice_level=1, typical_calories=310, typical_price=100,
         meals=["breakfast", "snack"], image_url=_IMG.format("photo-1610192244261-3f33de3f55e4")),
]


def seed() -> int:
    """Insert new concepts and refresh mutable fields on existing ones."""
    init_db()
    added = 0
    with Session(engine) as db:
        by_name = {c.name: c for c in db.exec(select(DishConcept)).all()}
        for row in CONCEPTS:
            current = by_name.get(row["name"])
            if current is None:
                db.add(DishConcept(**row))
                added += 1
            else:
                for k, v in row.items():
                    setattr(current, k, v)
                db.add(current)
        db.commit()
    return added


if __name__ == "__main__":
    n = seed()
    print(f"seeded {n} new dish concepts ({len(CONCEPTS)} total defined)")
