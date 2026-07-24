import logging

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.auth.deps import current_user
from app.db import get_session
from app.models import Profile, User
from app.schemas import OnboardIn, ProfileIn, UserOut

router = APIRouter(tags=["profile"])
log = logging.getLogger("kya.profile")


def _upsert_profile(db: Session, user_id: int, data: dict) -> Profile:
    profile = db.get(Profile, user_id)
    if profile is None:
        profile = Profile(user_id=user_id, **data)
        db.add(profile)
    else:
        for key, value in data.items():
            setattr(profile, key, value)
    return profile


@router.post("/onboard", response_model=UserOut)
def onboard(
    body: OnboardIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_session),
) -> User:
    """Save the signed-in user's permanent profile from onboarding."""
    if body.swiggy_address_id:
        user.swiggy_address_id = body.swiggy_address_id
    if body.swiggy_token:
        user.swiggy_token = body.swiggy_token
    db.add(user)

    _upsert_profile(db, user.id, body.profile.model_dump())
    db.commit()
    db.refresh(user)
    log.info("onboarded · user=%s", user.id)
    return user


@router.put("/profile", response_model=ProfileIn)
def update_profile(
    body: ProfileIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_session),
) -> Profile:
    profile = _upsert_profile(db, user.id, body.model_dump())
    db.commit()
    db.refresh(profile)
    return profile
