"""
Request/response shapes for the API — the mirror of the frontend's types.

Validation lives here rather than in the routers: a value that can't be right
should be rejected before any handler sees it, and `Literal` keeps the accepted
vocabulary visible in one place (and in the generated OpenAPI docs).
"""

from typing import Literal

from pydantic import BaseModel, Field

Diet = Literal["non_veg", "veg", "eggetarian", "vegan", "jain"]
Goal = Literal[
    "just_decide", "healthier", "lose_weight", "gain_muscle", "save_money", "try_new"
]
BudgetBand = Literal["under_200", "b200_350", "b350_500", "above_500", "ask"]
AdventureLevel = Literal[
    "mostly_familiar", "familiar_variety", "explore_often", "surprise_me"
]
# The day, as Indian eating actually splits it. `snack` is the 4–7pm chai/snack
# window (not "any small dish"), and `late_night` is the post-11pm one — without
# them a 4pm open reads as dinner, which is the wrong deck entirely.
MealPeriod = Literal["breakfast", "lunch", "snack", "dinner", "late_night"]
SwipeDirection = Literal["right", "left"]


class ProfileIn(BaseModel):
    diet: Diet = "non_veg"
    allergies: list[str] = Field(default_factory=list, max_length=40)
    avoided_ingredients: list[str] = Field(default_factory=list, max_length=40)
    restrictions: list[str] = Field(default_factory=list, max_length=40)
    goal: Goal = "just_decide"
    budget_band: BudgetBand = "b200_350"
    cuisines: list[str] = Field(default_factory=list, max_length=40)
    adventure_level: AdventureLevel = "familiar_variety"
    spice_level: int = Field(default=2, ge=0, le=4)  # 0 mild .. 4 devil mode
    # Optional body metrics + home region. Null when the user skipped those steps;
    # the bounds only exist to reject typos that would produce a nonsense BMI.
    height_cm: int | None = Field(default=None, ge=50, le=280)
    weight_kg: int | None = Field(default=None, ge=20, le=400)
    home_state: str | None = Field(default=None, max_length=64)


class RequestOtpIn(BaseModel):
    phone: str = Field(max_length=20)


class RequestOtpOut(BaseModel):
    ok: bool
    # Only populated by the "console" SMS provider so dev can proceed without
    # digging through the server log. Never returned by a real provider.
    dev_code: str | None = None


class VerifyOtpIn(BaseModel):
    phone: str = Field(max_length=20)
    code: str = Field(max_length=12)


class GoogleAuthIn(BaseModel):
    id_token: str = Field(max_length=4096)


class DeviceAuthIn(BaseModel):
    device_id: str = Field(max_length=128)


class AuthOut(BaseModel):
    token: str
    user_id: int
    phone: str | None = None
    onboarded: bool


class AddressOut(BaseModel):
    id: str
    label: str
    line: str


class SetAddressIn(BaseModel):
    address_id: str = Field(max_length=128)


class OnboardIn(BaseModel):
    swiggy_address_id: str | None = Field(default=None, max_length=128)
    # Normally set later by a Swiggy OAuth callback; accepted here so a connected
    # account can be wired in one step during testing.
    swiggy_token: str | None = None
    profile: ProfileIn


class UserOut(BaseModel):
    id: int
    phone: str | None = None  # Google users have no phone
    swiggy_address_id: str | None


class DeckRequest(BaseModel):
    """This meal's context. The user comes from the session token, not the body."""

    mood: str | None = Field(default=None, max_length=32)
    hunger: str | None = Field(default=None, max_length=32)
    meal: MealPeriod | None = None  # from the client's clock
    budget_override: int | None = Field(default=None, ge=0, le=100_000)
    companions: str | None = Field(default=None, max_length=32)
    time_available_min: int | None = Field(default=None, ge=0, le=600)


class CardOut(BaseModel):
    card_id: int
    name: str
    restaurant: str
    price: int
    eta_minutes: int | None
    rating: float | None
    image_url: str | None
    cuisine: str
    is_veg: bool
    is_ad: bool
    offer: str | None = None
    reason: str  # "why this fits you now"
    allergens: list[str]


class DeckOut(BaseModel):
    deck_id: int
    session_id: int
    sequence: int
    cards: list[CardOut]


class SwipeIn(BaseModel):
    card_id: int
    direction: SwipeDirection
    rejection_reason: str | None = Field(default=None, max_length=64)


class CartRequest(BaseModel):
    card_id: int
    quantity: int = Field(default=1, ge=1, le=20)


class CartOut(BaseModel):
    ok: bool
    restaurant: str
    item: str
    price: int  # the dish's menu price — pre-tax, pre-fees, one item
    quantity: int
    # Where to finish checkout — Kya Khaoon builds the cart, Swiggy takes payment.
    checkout_url: str
    # Swiggy's real payable total and its breakdown, read back from the live cart
    # after the add. All None when Swiggy didn't tell us — the client then shows
    # the menu price alone rather than a made-up total.
    total: int | None = None
    item_total: int | None = None
    taxes: int | None = None
    delivery_fee: int | None = None
    packing_fee: int | None = None
    platform_fee: int | None = None
    discount: int | None = None
