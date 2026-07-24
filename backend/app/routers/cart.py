import logging

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.auth.deps import current_user
from app.config import get_settings
from app.db import get_session
from app.errors import ConflictError, NotFoundError, UpstreamError, ValidationError
from app.models import DeckCard, DishConcept, Offer, User
from app.schemas import CartOut, CartRequest
from app.swiggy import swiggy_for_user
from app.swiggy.oauth import ensure_fresh

router = APIRouter(tags=["cart"])
log = logging.getLogger("kya.cart")

# Kya Khaoon owns the decision, not the transaction: we add the chosen dish to
# the user's Swiggy cart and hand off. Placing and paying for the order happens
# in Swiggy — there is deliberately no order-placement endpoint here.
SWIGGY_CHECKOUT_URL = "https://www.swiggy.com/checkout"


@router.post("/cart", response_model=CartOut)
async def add_to_cart(
    body: CartRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_session),
) -> CartOut:
    if get_settings().swiggy_mcp_url and not user.swiggy_token:
        raise ConflictError("connect your Swiggy account first")
    if not user.swiggy_address_id:
        raise ValidationError("user has no Swiggy delivery address selected")

    card = db.get(DeckCard, body.card_id)
    if card is None or card.offer_id is None:
        raise NotFoundError("card or its offer not found")
    offer = db.get(Offer, card.offer_id)
    concept = db.get(DishConcept, card.dish_concept_id)
    if offer is None or concept is None:
        raise NotFoundError("offer or dish not found")

    token = await ensure_fresh(db, user)
    client = swiggy_for_user(user)
    try:
        await client.add_to_cart(
            address_id=user.swiggy_address_id,
            restaurant_id=offer.restaurant_id,
            restaurant_name=offer.restaurant_name,
            menu_item_id=offer.menu_item_id,
            quantity=body.quantity,
            user_token=token,
        )
    except Exception as e:
        log.exception("cart add failed · user=%s card=%s", user.id, body.card_id)
        raise UpstreamError("Couldn't add this to your Swiggy cart.") from e

    log.info(
        "cart add · user=%s dish=%r qty=%s", user.id, concept.name, body.quantity
    )

    # Read back what Swiggy will actually charge. The menu price we showed on the
    # card is one dish pre-tax; the cart adds GST, delivery, packing and platform
    # fees (and applies real offers), so this is the only honest total. Best-effort
    # — the item IS in the cart either way, so a failure here must not 502.
    bill = None
    try:
        bill = await client.get_cart(user_token=token)
    except Exception as e:
        log.warning("cart-total fetch failed (%s); showing menu price only", e)

    return CartOut(
        ok=True,
        restaurant=offer.restaurant_name,
        item=concept.name,
        price=offer.price,
        quantity=body.quantity,
        checkout_url=SWIGGY_CHECKOUT_URL,
        total=bill.total if bill else None,
        item_total=bill.item_total if bill else None,
        taxes=bill.taxes if bill else None,
        delivery_fee=bill.delivery_fee if bill else None,
        packing_fee=bill.packing_fee if bill else None,
        platform_fee=bill.platform_fee if bill else None,
        discount=bill.discount if bill else None,
    )
