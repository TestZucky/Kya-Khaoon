"""
LLM picks carry real metadata, and the deterministic scorer ranks them.

Before this, generated dishes landed on column defaults (heaviness 3, spice 2,
meals []), so mood/meal/spice/budget scoring was a no-op on the live path — the
prompt was the only thing steering. Now the model describes each dish and the
scorer picks the final five.

Proves: the model's fields are persisted; out-of-range values are clamped rather
than trusted; and a dish that fits the user's budget, heat and meal time outranks
one the model offered that doesn't.

Run:  python -m tests.test_llm_ranking
"""

import asyncio
import os

from tests.dbsetup import fresh_db, use_test_db  # noqa: E402

use_test_db()
os.environ["OPENAI_API_KEY"] = "test-key"  # presence only; chat_json is mocked

from sqlmodel import Session, select  # noqa: E402

from app.db import engine  # noqa: E402
from app.models import DishConcept, Profile, User  # noqa: E402
from app.models import Session as MealSession  # noqa: E402
from app.recommend import llm_concepts  # noqa: E402
from app.recommend.deck import _rank_llm_picks  # noqa: E402


def _pick(name, **over):
    base = dict(
        name=name,
        search_query=name.lower(),
        cuisine="Indian",
        is_veg=True,
        contains=[],
        why=f"{name} is great",
        combo="",
        cooking_style="curry",
        heaviness=3,
        spice_level=1,
        typical_price=250,
        typical_calories=500,
        meals=["lunch"],
        ingredients=["rice", "spices"],
    )
    base.update(over)
    return base


# Three candidates for a mild-eating, ₹200-350, lunchtime user.
MOCK = {
    "picks": [
        # Fits everything.
        _pick("Perfect Thali"),
        # Way too hot and well over budget.
        _pick("Fiery Feast", spice_level=4, typical_price=1200),
        # A breakfast-only dish offered at lunch.
        _pick("Morning Poha", meals=["breakfast"], cooking_style="fried"),
        # Junk values the model should never send — must be clamped, not stored.
        _pick(
            "Garbage Numbers",
            heaviness=99,
            spice_level=-7,
            typical_price=-40,
            typical_calories=999999,
            meals=["brunch"],  # not a real meal period
        ),
    ]
}


async def _fake_chat_json(system, user, schema, **kw):
    return MOCK


def main() -> None:
    fresh_db()
    llm_concepts.chat_json = _fake_chat_json  # type: ignore[assignment]

    with Session(engine) as db:
        # Profile.user_id and Session.user_id are real foreign keys. SQLite left
        # them unenforced, so this test used to invent user_id=1 with no such
        # row; Postgres rejects that. Create the user the rows point at.
        user = User()
        db.add(user)
        db.commit()
        db.refresh(user)

        profile = Profile(
            user_id=user.id, diet="veg", budget_band="b200_350", spice_level=1
        )
        session = MealSession(user_id=user.id, meal="lunch")
        db.add(profile)
        db.add(session)
        db.commit()

        picks = asyncio.run(
            llm_concepts.generate_concepts(db, profile, session, [], limit=8)
        )
        assert len(picks) == 4, f"expected all 4 candidates, got {len(picks)}"

        stored = {c.name: c for c in db.exec(select(DishConcept)).all()}

        # --- the model's own numbers are kept, not defaulted ---
        fiery = stored["Fiery Feast"]
        assert fiery.spice_level == 4, fiery.spice_level
        assert fiery.typical_price == 1200, fiery.typical_price
        assert stored["Morning Poha"].meals == ["breakfast"]
        assert stored["Perfect Thali"].cooking_style == "curry"
        assert "rice" in stored["Perfect Thali"].ingredients
        print("  ok  model-supplied metadata persisted (no silent defaults)")

        # --- junk is clamped into range, and a bogus meal period dropped ---
        junk = stored["Garbage Numbers"]
        assert junk.heaviness == 5, junk.heaviness
        assert junk.spice_level == 0, junk.spice_level
        assert junk.typical_price == 20, junk.typical_price  # negative → lower bound
        assert junk.typical_calories == 3000, junk.typical_calories
        assert junk.meals == [], junk.meals
        print("  ok  out-of-range values clamped, unknown meal period dropped")

        # --- the scorer now actually ranks them ---
        ranked = _rank_llm_picks(
            picks,
            profile,
            session,
            recent_cuisines=set(),
            recent_styles=set(),
            limit=3,
        )
        order = [s.concept.name for s in ranked]
        print("ranked:", order)

        assert order[0] == "Perfect Thali", f"best-fitting dish didn't win: {order}"
        assert len(ranked) == 3, "limit not applied"
        # The too-hot, over-budget dish doesn't just rank low — it misses the cut.
        assert "Fiery Feast" not in order, f"unfit dish still made the deck: {order}"
        print("  ok  the dish fitting budget + heat + meal time ranks first")
        print("  ok  the too-hot, over-budget dish is dropped from the deck")

        # And with room for everyone, it still comes last.
        full = [
            s.concept.name
            for s in _rank_llm_picks(
                picks,
                profile,
                session,
                recent_cuisines=set(),
                recent_styles=set(),
                limit=4,
            )
        ]
        assert full[-1] == "Fiery Feast", f"worst-fitting dish not last: {full}"
        print("  ok  given room for all four, the worst fit ranks last")

        # --- the LLM's warmer `why` survives the re-ranking ---
        assert "is great" in ranked[0].reasons[0], ranked[0].reasons
        print("  ok  LLM reason kept; only the ordering comes from scoring")

    print("\nLLM RANKING TESTS PASSED ✅")
    if os.path.exists("./llmrank_test.db"):
        os.remove("./llmrank_test.db")


if __name__ == "__main__":
    main()
