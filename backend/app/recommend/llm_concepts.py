"""
Stage 1, LLM edition — OpenAI generates the 5 dishes.

The model gets the taste profile + the current moment and returns specific dishes
(with a `search_query` we resolve on Swiggy). Two safety layers:

  1. the prompt states allergies/diet as HARD rules, and
  2. we post-filter the model's output against the declared allergies/diet —
     because models hallucinate, and a peanut allergy is not a maybe.

Generated dishes are upserted into `dishconcept` so the rest of the pipeline
(resolve → persist → variety) treats them exactly like seeded ones.

Honest limitation: allergen detection relies on the model's self-reported
`contains` list. It's far better than nothing, but true zero-tolerance needs a
verified ingredient source, which neither we nor Swiggy have yet.
"""

from sqlmodel import Session, select

from app.llm.openai_client import chat_json
from app.models import DishConcept, Profile
from app.models import Session as MealSession
from app.recommend.concepts import (
    ScoredConcept,
    bmi_of,
    budget_ceiling,
    passes_hard_filters,
)

_VEG_DIETS = {"veg", "vegan", "jain"}
_MEAL_PERIODS = {"breakfast", "lunch", "snack", "dinner", "late_night"}


def _clamp(value: object, lo: int, hi: int, default: int) -> int:
    """A model-supplied int, forced into range. Junk or missing → `default`."""
    try:
        return max(lo, min(hi, int(value)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default

# Profile.spice_level (0..4) as words — the model reasons about "mild" far better
# than about the number 0.
_SPICE_WORDS = ["mild", "medium", "spicy", "extra hot", "very hot (devil mode)"]

# Meal periods as the model should read them. The tokens are the app's, the
# glosses are what actually tells it what to cook up for this hour.
_MEAL_WORDS = {
    "breakfast": "breakfast",
    "lunch": "lunch",
    "snack": "evening snack time (the 4-7pm chai-and-snack hour)",
    "dinner": "dinner",
    "late_night": "late night (past 11pm)",
}

_SCHEMA = {
    "type": "object",
    "properties": {
        "picks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "search_query": {"type": "string"},
                    "cuisine": {"type": "string"},
                    "is_veg": {"type": "boolean"},
                    "contains": {"type": "array", "items": {"type": "string"}},
                    "why": {"type": "string"},
                    "combo": {"type": "string"},
                    # The fields the deterministic scorer ranks on. Leave any of
                    # them out and generated dishes fall back to the column
                    # defaults, which makes mood/meal/spice/budget scoring a no-op.
                    "cooking_style": {
                        "type": "string",
                        "enum": [
                            "rice",
                            "fried",
                            "grilled",
                            "curry",
                            "noodles",
                            "baked",
                            "bowl",
                            "wrap",
                            "bread",
                            "snack",
                            "sweet",
                            "beverage",
                        ],
                    },
                    "heaviness": {"type": "integer", "minimum": 1, "maximum": 5},
                    "spice_level": {"type": "integer", "minimum": 0, "maximum": 4},
                    "typical_price": {"type": "integer"},
                    "typical_calories": {"type": "integer"},
                    "meals": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "breakfast",
                                "lunch",
                                "snack",
                                "dinner",
                                "late_night",
                            ],
                        },
                    },
                    "ingredients": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "name",
                    "search_query",
                    "cuisine",
                    "is_veg",
                    "contains",
                    "why",
                    "combo",
                    "cooking_style",
                    "heaviness",
                    "spice_level",
                    "typical_price",
                    "typical_calories",
                    "meals",
                    "ingredients",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["picks"],
    "additionalProperties": False,
}

_SYSTEM = (
    "You are the food-picking brain for Kya Khaoon, an app that decides what an "
    "Indian user should eat right now and orders it on Swiggy. Given their taste "
    "profile and the current moment, pick specific dishes they'd love right now. "
    "A deterministic scorer ranks your candidates and keeps the best five, so "
    "offer genuine variety rather than five versions of one idea.\n"
    "Rules:\n"
    "- SAFETY, never violate: never suggest anything containing a listed allergy or "
    "avoided ingredient. If the user is vegetarian/vegan/Jain, every pick must fit. "
    "Set is_veg correctly and list likely allergens in `contains` (lowercase, e.g. "
    "dairy, gluten, nuts, peanuts, soy, fish, egg, shellfish).\n"
    "- Fit the meal time. The five periods are breakfast, lunch, snack (the 4-7pm "
    "chai-and-snack hour — chaat, samosa, rolls, momos, not a full thali), dinner, "
    "and late_night (11pm onward — quick, comforting, widely open). Breakfast "
    "dishes only at breakfast; don't headline the snack hour with a heavy meal.\n"
    "- Respect the spice tolerance: don't headline a deck with fiery dishes for "
    "someone who eats mild.\n"
    "- Stay near the budget. Favour variety over what they ate recently.\n"
    "- Be real and specific — dishes actually available on Swiggy in urban India. "
    "`search_query` is 2-4 words we type into Swiggy search (e.g. 'chicken shawarma "
    "bowl').\n"
    "- `why`: one warm sentence, <= 12 words, on why it fits them now.\n"
    "- `combo`: optional small pairing, or an empty string.\n"
    "- Describe the dish honestly for ranking — these are re-checked against the "
    "user's profile, so guessing badly costs the pick: `heaviness` 1 (light salad) "
    "to 5 (biryani, thali); `spice_level` 0 (no chilli) to 4 (fiery); "
    "`typical_price` the usual Swiggy price in rupees for one portion; "
    "`typical_calories` a rough per-portion estimate; `meals` every meal period it "
    "genuinely suits; `ingredients` 3-6 main ones, lowercase (say 'protein' for a "
    "high-protein dish); `cooking_style` the closest match from the list.\n"
    "- When a home region is given, lean into that region's comfort food where it "
    "fits the moment (someone from Punjab may crave a home dish).\n"
    "- If a BMI category is given, tilt (never restrict) toward it: lighter, "
    "higher-protein picks for overweight/obese; heartier for underweight. Health "
    "is a nudge, never a lecture — keep `why` warm, never mention their BMI.\n"
    "- When their order history is given, use it: echo dishes/cuisines they clearly "
    "love, respect their usual spend, and avoid what they just ordered."
)


def _build_user_prompt(
    profile: Profile,
    session: MealSession,
    recent: list[str],
    order_summary: str | None = None,
) -> str:
    cap = budget_ceiling(profile, session)
    lines = [
        f"Diet: {profile.diet}",
        f"Allergies (NEVER suggest): {', '.join(profile.allergies) or 'none'}",
        f"Avoid: {', '.join(profile.avoided_ingredients) or 'none'}",
        f"Favourite cuisines: {', '.join(profile.cuisines) or 'open to anything'}",
        f"Goal: {profile.goal}",
        f"Spice tolerance: {_SPICE_WORDS[profile.spice_level]}"
        if 0 <= profile.spice_level < len(_SPICE_WORDS)
        else "Spice tolerance: medium",
        f"Budget: up to ₹{cap} per meal" if cap else "Budget: flexible",
        f"Meal right now: {_MEAL_WORDS.get(session.meal or '', session.meal or 'unspecified')}",
    ]
    if profile.home_state:
        lines.append(f"Home region: {profile.home_state}")
    bmi = bmi_of(profile)
    if bmi:
        lines.append(f"BMI: {bmi[0]} ({bmi[1]})")
    if session.mood:
        lines.append(f"Mood: {session.mood}")
    if session.hunger:
        lines.append(f"Hunger: {session.hunger}")
    if session.companions:
        lines.append(f"Eating with: {session.companions}")
    if order_summary:
        lines.append(f"Order history: {order_summary}")
    if recent:
        lines.append(f"Ate/saw recently (offer variety): {', '.join(recent[:8])}")
    return "\n".join(lines)


def _allergic(contains: list[str], profile: Profile) -> bool:
    blocked = {a.lower() for a in profile.allergies + profile.avoided_ingredients}
    for c in (x.lower() for x in contains):
        for b in blocked:
            if b and (b in c or c in b):
                return True
    return False


async def generate_concepts(
    db: Session,
    profile: Profile,
    session: MealSession,
    recent: list[str],
    *,
    order_summary: str | None = None,
    limit: int = 5,
) -> list[ScoredConcept]:
    prompt = (
        f"{_build_user_prompt(profile, session, recent, order_summary)}\n"
        f"Return exactly {limit} dishes."
    )
    # Budget tokens per dish, not per request: a flat cap truncates the JSON
    # mid-string once the list is long enough, and a half-parsed response drops
    # the whole deck to the rules fallback. ~190 tokens/dish measured, doubled.
    data = await chat_json(_SYSTEM, prompt, _SCHEMA, max_tokens=400 * limit + 400)

    veg_required = profile.diet in _VEG_DIETS
    existing = {c.name: c for c in db.exec(select(DishConcept)).all()}
    out: list[ScoredConcept] = []

    for p in data.get("picks", []):
        if len(out) >= limit:
            break
        # Safety post-filter — the belt to the prompt's suspenders.
        if veg_required and not p.get("is_veg"):
            continue
        if _allergic(p.get("contains", []), profile):
            continue

        name = p["name"].strip()
        concept = existing.get(name)
        fields = dict(
            name=name,
            search_query=p["search_query"].strip(),
            cuisine=p.get("cuisine", "").strip() or "Other",
            cooking_style=(p.get("cooking_style") or "").strip() or "generated",
            is_veg=bool(p.get("is_veg")),
            allergens=[a.lower() for a in p.get("contains", [])],
            ingredients=[i.lower().strip() for i in p.get("ingredients", []) if i],
            meals=[m for m in p.get("meals", []) if m in _MEAL_PERIODS],
            # Clamped, not trusted: a model that returns heaviness 9 or a negative
            # price would otherwise skew every score it touches.
            heaviness=_clamp(p.get("heaviness"), 1, 5, 3),
            spice_level=_clamp(p.get("spice_level"), 0, 4, 2),
            typical_price=_clamp(p.get("typical_price"), 20, 5000, 300),
            typical_calories=_clamp(p.get("typical_calories"), 50, 3000, 500),
        )
        if concept is None:
            concept = DishConcept(**fields)
            db.add(concept)
        else:
            for k, v in fields.items():
                setattr(concept, k, v)
        db.flush()  # assign id
        existing[name] = concept

        why = p.get("why", "").strip() or "A great pick for right now"
        combo = p.get("combo", "").strip()
        reason = f"{why} — pair with {combo}" if combo else why
        out.append(ScoredConcept(concept=concept, score=0.0, reasons=[reason]))

    # Final safety net: never let a hard-filter violation through, whatever the
    # model said about is_veg/contains.
    return [s for s in out if passes_hard_filters(s.concept, profile)]
