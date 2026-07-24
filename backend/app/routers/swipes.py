from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.auth.deps import current_user
from app.db import get_session
from app.errors import NotFoundError
from app.models import DeckCard, Swipe, User
from app.schemas import SwipeIn

router = APIRouter(tags=["swipes"])


@router.post("/swipes", status_code=201)
def record_swipe(
    body: SwipeIn,
    _user: User = Depends(current_user),
    db: Session = Depends(get_session),
) -> dict[str, int]:
    """
    Record a swipe. Right = intent to order (never auto-orders), left = reject,
    optionally with a reason that trains future decks. History is stored even
    though the app shows no history screen; it's the learning signal.
    """
    if db.get(DeckCard, body.card_id) is None:
        raise NotFoundError("card not found")

    swipe = Swipe(
        deck_card_id=body.card_id,
        direction=body.direction,
        rejection_reason=body.rejection_reason if body.direction == "left" else None,
    )
    db.add(swipe)
    db.commit()
    db.refresh(swipe)
    return {"swipe_id": swipe.id}
