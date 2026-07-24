"""
Stage 1 — pick five dish *concepts* from our own catalogue, before Swiggy.

The filter pipeline, in order:

  1. hard safety      allergies / diet / avoided ingredients  → eliminate, never score
  2. context          budget, mood, hunger                    → what "good" means now
  3. taste            favourite cuisines, spice match         → likely enjoyment
  4. variety penalty  repetition across cuisine/style/ingredient
  5. routine/occasion small nudges

Deterministic and debuggable on purpose — an allergy must be a hard exclusion, not
a low score, so no language model sits in this path.
"""

from dataclasses import dataclass

from app.models import DishConcept, Profile, Session

_VEG_DIETS = {"veg", "vegan", "jain"}

# Bands that cap spend. "above_500" and "ask" have no ceiling → not listed.
_BUDGET_MAX = {
    "under_200": 200,
    "b200_350": 350,
    "b350_500": 500,
}
NO_CAP = 10**9  # stand-in ceiling for scoring when the band is uncapped

# Mood → the dish heaviness (1 light .. 5 heavy) it implies. The picker offers
# more moods than this: any mood not listed simply gets no heaviness nudge and is
# still sent to the LLM verbatim, which reads "craving something spicy" better
# than a scalar does.
_MOOD_HEAVINESS = {
    "comfort": 5,
    "indulgent": 5,
    "hearty": 5,
    "cozy": 4,
    "adventurous": 3,
    "quick": 2,
    "healthy": 2,
    "light": 1,
    "fresh": 1,
}


# The card reason for a dish that fits the current period. Lunch and dinner get
# none — "a good dinner pick" at dinner is noise, where "a good breakfast pick"
# genuinely narrows what's on offer.
_MEAL_REASON = {
    "breakfast": "A good breakfast pick",
    "snack": "Right for the evening snack hour",
    "late_night": "Still good this late",
}

# Periods whose dishes are an acceptable second choice when nothing is tagged for
# the current one. Deliberately asymmetric: dinner food works late at night, but
# a late-night bite shouldn't headline a dinner deck.
_MEAL_ALSO_FITS = {
    "snack": {"breakfast"},
    "late_night": {"snack", "dinner"},
}


@dataclass
class ScoredConcept:
    concept: DishConcept
    score: float
    reasons: list[str]


def bmi_of(profile: Profile) -> tuple[float, str] | None:
    """
    (BMI, category) from the profile's height/weight, or None when either is
    missing (the user skipped that step). Category uses the standard WHO bands.
    """
    h, w = profile.height_cm, profile.weight_kg
    if not h or not w:
        return None
    bmi = round(w / (h / 100) ** 2, 1)
    if bmi < 18.5:
        cat = "underweight"
    elif bmi < 25:
        cat = "healthy"
    elif bmi < 30:
        cat = "overweight"
    else:
        cat = "obese"
    return bmi, cat


def budget_ceiling(profile: Profile, session: Session) -> int | None:
    """
    This meal's spend cap in rupees, or None when the band is uncapped
    (above_500 / ask) and no session override. A session override always caps.
    """
    if session.budget_override:
        return session.budget_override
    return _BUDGET_MAX.get(profile.budget_band)


def passes_hard_filters(c: DishConcept, profile: Profile) -> bool:
    """Safety and diet. Any failure removes the concept outright."""
    if profile.diet in _VEG_DIETS and not c.is_veg:
        return False
    if set(c.allergens) & set(profile.allergies):
        return False
    if set(c.ingredients) & set(profile.avoided_ingredients):
        return False
    return True


def select_concepts(
    concepts: list[DishConcept],
    profile: Profile,
    session: Session,
    *,
    recent_cuisines: set[str] | None = None,
    recent_styles: set[str] | None = None,
    exclude_ids: set[int] | None = None,
    limit: int = 5,
) -> list[ScoredConcept]:
    recent_cuisines = recent_cuisines or set()
    recent_styles = recent_styles or set()
    exclude_ids = exclude_ids or set()

    ceiling = budget_ceiling(profile, session) or NO_CAP
    mood_target = _MOOD_HEAVINESS.get(session.mood or "")
    favourites = {c.lower() for c in profile.cuisines}
    home = (profile.home_state or "").lower()
    bmi = bmi_of(profile)

    scored: list[ScoredConcept] = []
    for c in concepts:
        if c.id in exclude_ids or not passes_hard_filters(c, profile):
            continue

        score = 0.0
        reasons: list[str] = []

        # 2 — context: budget, mood and meal time.
        # Budget only affects the *score* here — the "within budget" reason is
        # asserted later against the real resolved price, never the typical one,
        # so a card never claims a budget it doesn't actually meet.
        if c.typical_price <= ceiling:
            score += 2.0
        else:
            score -= 3.0  # over budget: strongly discouraged, not eliminated
        if mood_target is not None:
            score += 1.5 - 0.4 * abs(c.heaviness - mood_target)
            if abs(c.heaviness - mood_target) <= 1 and session.mood:
                reasons.append(f"Matches your {session.mood} mood")

        # Meal time (from the client's clock). A breakfast dish shouldn't headline
        # a dinner deck, and vice-versa — strong nudge, not a hard filter.
        if session.meal and c.meals:
            if session.meal in c.meals:
                score += 2.0
                reason = _MEAL_REASON.get(session.meal)
                if reason:
                    reasons.append(reason)
            elif set(c.meals) & _MEAL_ALSO_FITS.get(session.meal, set()):
                # An adjacent period — half the bonus, no penalty. Keeps a late
                # night from scoring every dish identically just because almost
                # nothing is explicitly tagged for it.
                score += 1.0
            else:
                score -= 3.0

        # 3 — taste
        if c.cuisine.lower() in favourites:
            score += 2.5
            reasons.append(f"You love {c.cuisine}")

        # Heat tolerance. Too hot is a real problem (an inedible meal), too mild
        # is only a mild disappointment — so the penalties are asymmetric. Never
        # a hard filter: someone on "medium" should still see a great vindaloo.
        heat_gap = c.spice_level - profile.spice_level
        if heat_gap > 0:
            score -= 1.2 * heat_gap
        elif heat_gap < 0:
            score -= 0.3 * abs(heat_gap)
        else:
            score += 0.8
            reasons.append("Spiced how you like it")

        # 4 — variety penalty
        if c.cuisine.lower() in recent_cuisines:
            score -= 2.0
        else:
            reasons.append("A change from your recent meals")
        if c.cooking_style.lower() in recent_styles:
            score -= 1.5

        # 5 — goal nudges
        if profile.goal in {"healthier", "lose_weight"} and c.heaviness <= 2:
            score += 1.0
            reasons.append("Lighter pick for your goal")
        if profile.goal == "gain_muscle" and "protein" in c.ingredients:
            score += 1.0
            reasons.append("High protein")

        # Home-region comfort nudge — light substring match on cuisine/name (the
        # LLM path handles this far better; here it's just a small tilt).
        if home and (home in c.cuisine.lower() or home in c.name.lower()):
            score += 1.0
            reasons.append(f"A taste of home ({profile.home_state})")

        # BMI nudge — lighter picks tilt for higher BMI, heartier for underweight.
        if bmi:
            cat = bmi[1]
            if cat in {"overweight", "obese"} and c.heaviness <= 2:
                score += 0.8
                reasons.append("A lighter pick")
            elif cat == "underweight" and c.heaviness >= 4:
                score += 0.8

        scored.append(ScoredConcept(c, score, reasons or ["A solid pick for now"]))

    scored.sort(key=lambda s: s.score, reverse=True)
    return scored[:limit]
