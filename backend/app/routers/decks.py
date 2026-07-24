import logging

from fastapi import APIRouter, Depends
from sqlmodel import Session as DBSession

from app.auth.deps import current_user
from app.config import get_settings
from app.db import get_session
from app.errors import AppError, ConflictError, UpstreamError, ValidationError
from app.models import Profile, Session, User
from app.recommend.deck import build_deck
from app.schemas import CardOut, DeckOut, DeckRequest
from app.swiggy import swiggy_for_user
from app.swiggy.oauth import ensure_fresh

router = APIRouter(tags=["decks"])
log = logging.getLogger("kya.deck")


def _require_swiggy(user: User) -> None:
    """In real-Swiggy mode, don't serve fake data — make the user connect first."""
    if get_settings().swiggy_mcp_url and not user.swiggy_token:
        raise ConflictError("connect your Swiggy account first")


@router.post("/decks", response_model=DeckOut)
async def create_deck(
    body: DeckRequest,
    user: User = Depends(current_user),
    db: DBSession = Depends(get_session),
) -> DeckOut:
    _require_swiggy(user)
    if not user.swiggy_address_id:
        raise ValidationError("user has no Swiggy delivery address selected")
    profile = db.get(Profile, user.id)
    if profile is None:
        raise ValidationError("user has not completed onboarding")

    # Each deck opens a fresh temporary-context session.
    session = Session(
        user_id=user.id,
        mood=body.mood,
        hunger=body.hunger,
        meal=body.meal,
        budget_override=body.budget_override,
        companions=body.companions,
        time_available_min=body.time_available_min,
    )
    db.add(session)
    db.flush()

    token = await ensure_fresh(db, user)
    try:
        deck, cards = await build_deck(
            db,
            swiggy_for_user(user),
            user_id=user.id,
            address_id=user.swiggy_address_id,
            profile=profile,
            session=session,
            user_token=token,
        )
    except AppError:
        raise
    except Exception as e:
        # Stage 1 has its own fallback, so reaching here means Swiggy resolution
        # or persistence broke. Roll back so a half-written deck isn't left behind.
        db.rollback()
        log.exception("deck build failed · user=%s", user.id)
        raise UpstreamError("Couldn't build your picks right now.") from e

    if not cards:
        # Stage 1 had picks (or it would have raised), so every one of them failed
        # to resolve to an open listing. That's a real "nothing's available" answer.
        log.warning("deck empty after resolution · user=%s", user.id)
        raise UpstreamError(
            "Nothing we picked is available near you right now. Try again in a bit."
        )

    log.info("deck built · user=%s cards=%d meal=%s", user.id, len(cards), body.meal)

    return DeckOut(
        deck_id=deck.id,
        session_id=session.id,
        sequence=deck.sequence,
        cards=[
            CardOut(
                card_id=c.card_id,
                name=c.concept.name,
                restaurant=c.offer.restaurant_name,
                price=c.offer.price,
                eta_minutes=c.offer.eta_minutes,
                rating=c.offer.rating,
                image_url=c.offer.image_url,
                cuisine=c.concept.cuisine,
                is_veg=c.concept.is_veg,
                is_ad=c.offer.is_ad,
                offer=c.offer.offer,
                reason=c.reason,
                allergens=c.concept.allergens,
            )
            for c in cards
        ],
    )
