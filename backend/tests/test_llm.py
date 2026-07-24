"""
LLM stage-1 safety filter — deterministic, no real OpenAI call.

We feed a deliberately-unsafe model response (a non-veg dish and a dairy dish) for
a vegetarian, dairy-allergic user and prove both get filtered out, and that the
survivors are persisted as dish concepts the rest of the pipeline can use.

Run:  python -m tests.test_llm
"""

import asyncio
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./llm_test.db")
os.environ["OPENAI_API_KEY"] = "test-key"  # presence only; chat_json is mocked

from sqlmodel import Session, select  # noqa: E402

from app.db import engine, init_db  # noqa: E402
from app.models import DishConcept, Profile  # noqa: E402
from app.models import Session as MealSession  # noqa: E402
from app.recommend import llm_concepts  # noqa: E402

# What the "model" returns — includes two picks that must be filtered.
MOCK = {
    "picks": [
        {"name": "Masala Dosa", "search_query": "masala dosa", "cuisine": "South Indian",
         "is_veg": True, "contains": [], "why": "Crispy and light", "combo": "sambar"},
        {"name": "Paneer Tikka", "search_query": "paneer tikka", "cuisine": "North Indian",
         "is_veg": True, "contains": ["dairy"], "why": "Smoky and rich", "combo": ""},   # DAIRY → drop
        {"name": "Chicken Roll", "search_query": "chicken roll", "cuisine": "Indian",
         "is_veg": False, "contains": [], "why": "Hearty wrap", "combo": ""},            # NON-VEG → drop
        {"name": "Aloo Paratha", "search_query": "aloo paratha", "cuisine": "North Indian",
         "is_veg": True, "contains": ["gluten"], "why": "Comforting classic", "combo": "pickle"},
        {"name": "Veg Poha", "search_query": "poha", "cuisine": "Maharashtrian",
         "is_veg": True, "contains": ["peanuts"], "why": "Light and quick", "combo": ""},
    ]
}


async def _fake_chat_json(system, user, schema, **kw):
    return MOCK


def main() -> None:
    init_db()
    llm_concepts.chat_json = _fake_chat_json  # type: ignore[assignment]

    with Session(engine) as db:
        profile = Profile(
            user_id=1, diet="veg", allergies=["dairy"], budget_band="b200_350"
        )
        session = MealSession(user_id=1, meal="breakfast")
        db.add(profile)
        db.add(session)
        db.commit()

        picks = asyncio.run(
            llm_concepts.generate_concepts(db, profile, session, [], limit=5)
        )
        names = [p.concept.name for p in picks]
        print("survivors:", names)

        assert "Paneer Tikka" not in names, "dairy dish leaked to a dairy-allergic user"
        assert "Chicken Roll" not in names, "non-veg dish leaked to a veg user"
        assert "Masala Dosa" in names and "Aloo Paratha" in names
        assert all(p.concept.is_veg for p in picks)
        print("  ok  dairy + non-veg picks filtered out; veg-safe survivors kept")

        # Survivors are persisted concepts with a reason (why [+ combo]).
        stored = {c.name for c in db.exec(select(DishConcept)).all()}
        assert "Masala Dosa" in stored
        assert picks[0].reasons[0]  # non-empty why
        assert "sambar" in picks[0].reasons[0]  # combo folded into the reason
        print("  ok  survivors persisted as concepts with why + combo")

    print("\nLLM SAFETY TESTS PASSED ✅")
    if os.path.exists("./llm_test.db"):
        os.remove("./llm_test.db")


if __name__ == "__main__":
    main()
