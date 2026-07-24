"""
Spice tolerance in the deterministic scorer.

Onboarding asks for heat tolerance, so it has to actually move the ranking.
Proves: at equal everything-else a dish matching your tolerance outranks a much
hotter one; going too hot is penalised harder than going too mild (an inedible
meal beats a dull one as a failure); and it's a *nudge*, never a hard filter — a
fiery dish still survives into the candidate list.

Run:  python -m tests.test_spice
"""

import os

from tests.dbsetup import use_test_db  # noqa: E402

use_test_db()

from app.models import DishConcept, Profile  # noqa: E402
from app.models import Session as MealSession  # noqa: E402
from app.recommend.concepts import select_concepts  # noqa: E402


def _dish(id_: int, name: str, spice: int) -> DishConcept:
    """Identical on every axis except heat, so spice is the only variable."""
    return DishConcept(
        id=id_,
        name=name,
        search_query=name.lower(),
        cuisine="Indian",
        cooking_style="curry",
        is_veg=True,
        allergens=[],
        heaviness=3,
        spice_level=spice,
        typical_calories=500,
        typical_price=250,
        meals=["lunch", "dinner"],
    )


def main() -> None:
    profile = Profile(user_id=1, diet="veg", budget_band="b200_350", spice_level=1)
    session = MealSession(user_id=1)

    mild = _dish(1, "Mild Korma", 0)
    match = _dish(2, "Medium Masala", 1)
    fiery = _dish(3, "Devil Vindaloo", 4)

    scored = select_concepts([mild, match, fiery], profile, session, limit=10)
    by_name = {s.concept.name: s.score for s in scored}
    print("scores:", {k: round(v, 2) for k, v in by_name.items()})

    assert by_name["Medium Masala"] > by_name["Devil Vindaloo"], "too-hot dish not penalised"
    assert by_name["Medium Masala"] > by_name["Mild Korma"], "exact match should win"
    print("  ok  a dish at your tolerance outranks both hotter and milder")

    # Asymmetry: 3 steps too hot must cost more than 1 step too mild.
    too_hot_gap = by_name["Medium Masala"] - by_name["Devil Vindaloo"]
    too_mild_gap = by_name["Medium Masala"] - by_name["Mild Korma"]
    assert too_hot_gap > too_mild_gap, "too-hot should be penalised harder than too-mild"
    print("  ok  too hot is penalised harder than too mild")

    # Never a hard filter — the fiery dish is still a candidate.
    assert "Devil Vindaloo" in by_name, "spice must nudge, not exclude"
    print("  ok  hot dishes are ranked down, never hidden")

    # A chilli-head flips the order.
    hot_profile = Profile(user_id=2, diet="veg", budget_band="b200_350", spice_level=4)
    hot_scored = select_concepts([mild, match, fiery], hot_profile, session, limit=10)
    hot_by_name = {s.concept.name: s.score for s in hot_scored}
    assert hot_by_name["Devil Vindaloo"] > hot_by_name["Mild Korma"]
    print("  ok  a devil-mode profile ranks the fiery dish top")

    print("\nSPICE SCORING TESTS PASSED ✅")
    if os.path.exists("./spice_test.db"):
        os.remove("./spice_test.db")


if __name__ == "__main__":
    main()
