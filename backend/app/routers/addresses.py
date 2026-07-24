import logging

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.auth.deps import current_user
from app.db import get_session
from app.errors import AppError, UpstreamError, ValidationError
from app.models import User
from app.schemas import AddressOut, SetAddressIn
from app.swiggy import swiggy_for_user
from app.swiggy.oauth import ensure_fresh

router = APIRouter(tags=["addresses"])
log = logging.getLogger("kya.address")


async def _fetch(user: User, token: str | None) -> list:
    try:
        return await swiggy_for_user(user).get_addresses(user_token=token)
    except AppError:
        raise
    except Exception as e:
        log.exception("address fetch failed · user=%s", user.id)
        raise UpstreamError("Couldn't load your Swiggy addresses.") from e


@router.get("/addresses", response_model=list[AddressOut])
async def list_addresses(
    user: User = Depends(current_user),
    db: Session = Depends(get_session),
) -> list[AddressOut]:
    """The signed-in user's saved Swiggy delivery addresses."""
    token = await ensure_fresh(db, user)
    addresses = await _fetch(user, token)
    return [AddressOut(id=a.id, label=a.label, line=a.line) for a in addresses]


@router.post("/address", status_code=204)
async def choose_address(
    body: SetAddressIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_session),
) -> None:
    """Set the delivery address every menu/restaurant/cart call will use."""
    token = await ensure_fresh(db, user)
    valid = {a.id for a in await _fetch(user, token)}
    if body.address_id not in valid:
        raise ValidationError("unknown address")
    user.swiggy_address_id = body.address_id
    db.add(user)
    db.commit()
