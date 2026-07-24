"""
Database tables.

State is split three ways: PERMANENT identity/diet on Profile, LONG-TERM
tendencies on Routine, and TEMPORARY per-meal context on Session. Keeping them
apart is what lets "something light tonight" refine one deck without corrupting
"I am vegetarian".

List-valued columns use JSON rather than native Postgres arrays: variety logic
loads a row and computes in Python, so we never query inside these lists and the
extra indexing an array type would buy us goes unused.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.crypto import EncryptedString


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _json_list() -> Column:
    return Column(JSON, nullable=False, default=list)


# ── Identity ────────────────────────────────────────────────────────────────
class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    # A user is identified by phone (OTP), google_sub (Google), OR device_id — any
    # may be null. device_id is a UUID the browser generates and keeps in
    # localStorage: it remembers a *browser*, not a person, so it survives reloads
    # but not a new device or a storage wipe. Deliberate demo trade-off — attaching
    # a phone later upgrades the same row rather than creating a second one.
    phone: str | None = Field(default=None, index=True, unique=True)
    google_sub: str | None = Field(default=None, index=True, unique=True)
    device_id: str | None = Field(default=None, index=True, unique=True)
    email: str | None = None
    name: str | None = None
    # Chosen from the user's Swiggy addresses; every menu/restaurant search needs it.
    swiggy_address_id: str | None = None
    # The user's Swiggy MCP OAuth tokens, forwarded on their behalf to the remote
    # MCP server. Null until they connect Swiggy; the fake client ignores them.
    # Encrypted at rest — these act as the user on Swiggy, so a copy of this
    # table must not be enough to use them. See app/crypto.py.
    swiggy_token: str | None = Field(default=None, sa_type=EncryptedString)
    swiggy_refresh_token: str | None = Field(default=None, sa_type=EncryptedString)
    swiggy_token_expires_at: datetime | None = None
    created_at: datetime = Field(default_factory=_utcnow)


# ── Swiggy OAuth plumbing ───────────────────────────────────────────────────
class SwiggyOAuthClient(SQLModel, table=True):
    """Our dynamically-registered client_id at mcp.swiggy.com (register once)."""

    id: int | None = Field(default=None, primary_key=True)
    client_id: str
    created_at: datetime = Field(default_factory=_utcnow)


class SwiggyAuthFlow(SQLModel, table=True):
    """A pending authorize→callback round-trip: ties the state back to a user."""

    state: str = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    # The PKCE verifier is what proves the token request came from whoever
    # started the authorize — a credential too, so it gets the same treatment.
    code_verifier: str = Field(sa_type=EncryptedString)
    created_at: datetime = Field(default_factory=_utcnow)


# ── SMS OTP challenge (one row per phone, upserted on each request) ─────────
class OtpChallenge(SQLModel, table=True):
    phone: str = Field(primary_key=True)
    code_hash: str  # sha256(phone + code) — never store the code itself
    expires_at: datetime
    attempts: int = 0  # wrong verifies; the code is burned past the max
    last_sent_at: datetime = Field(default_factory=_utcnow)


# ── PERMANENT: diet, safety, stable taste ───────────────────────────────────
class Profile(SQLModel, table=True):
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    diet: str = "non_veg"  # non_veg | veg | eggetarian | vegan | jain
    allergies: list[str] = Field(default_factory=list, sa_column=_json_list())
    avoided_ingredients: list[str] = Field(default_factory=list, sa_column=_json_list())
    restrictions: list[str] = Field(default_factory=list, sa_column=_json_list())
    goal: str = "just_decide"  # just_decide | healthier | lose_weight | gain_muscle | save_money | try_new
    budget_band: str = "b200_350"  # under_200 | b200_350 | b350_500 | above_500 | ask
    cuisines: list[str] = Field(default_factory=list, sa_column=_json_list())
    adventure_level: str = "familiar_variety"  # mostly_familiar | familiar_variety | explore_often | surprise_me
    # Heat tolerance, 0 (mild) .. 4 (devil mode), matching DishConcept.spice_level.
    # Asked during onboarding; dishes hotter than this are scored down, not hidden.
    spice_level: int = 2
    # Optional body metrics + home region. height/weight drive BMI-aware picks;
    # home_state pulls in regional comfort food. All null when the user skips them.
    height_cm: int | None = None
    weight_kg: int | None = None
    home_state: str | None = None


# ── LONG-TERM: routine and lifestyle ────────────────────────────────────────
class Routine(SQLModel, table=True):
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    profession: str | None = None
    work_days: list[str] = Field(default_factory=list, sa_column=_json_list())
    work_mode: str | None = None  # office | hybrid | wfh
    lifestyle_habits: list[str] = Field(default_factory=list, sa_column=_json_list())


# ── TEMPORARY: one meal's context ───────────────────────────────────────────
class Session(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    mood: str | None = None  # comfort | light | adventurous | ...
    hunger: str | None = None  # snack | normal | very_hungry
    # Meal period, from the client's clock:
    # breakfast | lunch | snack (evening) | dinner | late_night.
    meal: str | None = None
    budget_override: int | None = None  # rupees, beats the profile band for this meal
    companions: str | None = None  # solo | partner | friends | family
    time_available_min: int | None = None
    created_at: datetime = Field(default_factory=_utcnow)


# ── Our decision vocabulary — SEEDED, not from Swiggy ───────────────────────
class DishConcept(SQLModel, table=True):
    """
    A dish *idea* ("chicken shawarma bowl"), not a specific listing. Stage 1 picks
    concepts from these; stage 2 resolves each to a live Swiggy offer. Everything
    Swiggy can't tell us — ingredients, cooking style, heaviness, allergens —
    lives here, which is exactly what the variety logic runs on.
    """

    id: int | None = Field(default=None, primary_key=True)
    name: str
    aliases: list[str] = Field(default_factory=list, sa_column=_json_list())
    search_query: str  # what we send to Swiggy's search
    cuisine: str
    ingredients: list[str] = Field(default_factory=list, sa_column=_json_list())
    cooking_style: str  # rice | fried | grilled | curry | noodles | baked | bowl | wrap
    is_veg: bool = False
    allergens: list[str] = Field(default_factory=list, sa_column=_json_list())
    heaviness: int = 3  # 1 (light) .. 5 (very heavy)
    spice_level: int = 2  # 0 .. 4
    typical_calories: int = 500
    typical_price: int = 300
    # Curated fallback image, used when the live offer has none (e.g. dev/fake).
    image_url: str = ""
    # Which meal periods this dish suits:
    # breakfast | lunch | snack (evening) | dinner | late_night.
    meals: list[str] = Field(default_factory=list, sa_column=_json_list())


# ── CACHE of a stage-2 resolution ───────────────────────────────────────────
class Offer(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    dish_concept_id: int = Field(foreign_key="dishconcept.id", index=True)
    address_id: str = Field(index=True)
    menu_item_id: str
    restaurant_id: str
    restaurant_name: str
    price: int  # menu price in rupees (final payable resolved at confirmation)
    eta_minutes: int | None = None
    rating: float | None = None
    image_url: str | None = None
    in_stock: bool = True
    is_ad: bool = False
    offer: str | None = None  # e.g. "50% OFF" — shown as a discount badge
    fetched_at: datetime = Field(default_factory=_utcnow)


# ── A generated deck and its cards ──────────────────────────────────────────
class Deck(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="session.id", index=True)
    sequence: int = 1  # deck 1, then 2 after a refresh
    created_at: datetime = Field(default_factory=_utcnow)


class DeckCard(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    deck_id: int = Field(foreign_key="deck.id", index=True)
    dish_concept_id: int = Field(foreign_key="dishconcept.id")
    offer_id: int | None = Field(default=None, foreign_key="offer.id")
    rank: int  # 0-based position in the deck
    reason: str  # "why this fits you now"


# ── Learning signals ────────────────────────────────────────────────────────
class Swipe(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    deck_card_id: int = Field(foreign_key="deckcard.id", index=True)
    direction: str  # right | left
    rejection_reason: str | None = None  # too_expensive | too_heavy | ate_recently | dislike_cuisine | not_in_mood
    created_at: datetime = Field(default_factory=_utcnow)


class MealFeedback(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    deck_card_id: int = Field(foreign_key="deckcard.id", index=True)
    verdict: str  # loved | okay | disliked | too_spicy | poor_value
    notes: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
