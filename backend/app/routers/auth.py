import logging
import re

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session, select

from app.auth.device import sign_in as device_sign_in
from app.auth.google import verify_id_token
from app.auth.otp import request_code, verify_code
from app.auth.tokens import issue_token
from app.config import get_settings
from app.db import get_session
from app.errors import UpstreamError, ValidationError
from app.logging_config import mask_email
from app.models import Profile, User
from app.schemas import (
    AuthOut,
    DeviceAuthIn,
    GoogleAuthIn,
    RequestOtpIn,
    RequestOtpOut,
    VerifyOtpIn,
)
from app.sms import get_sms_sender

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger("kya.auth")

# 10-digit Indian mobile (the frontend sends the national number, no +91).
_PHONE = re.compile(r"^\d{10}$")


def _normalise(phone: str) -> str:
    phone = phone.strip().replace(" ", "")
    if not _PHONE.match(phone):
        raise ValidationError("enter a 10-digit mobile number", status_code=422)
    return phone


@router.post("/request-otp", response_model=RequestOtpOut)
async def request_otp(
    body: RequestOtpIn, db: Session = Depends(get_session)
) -> RequestOtpOut:
    phone = _normalise(body.phone)
    code = request_code(db, phone)

    try:
        await get_sms_sender().send(
            to=f"+91{phone}", body=f"Your Kya Khaoon code is {code}. Valid 5 minutes."
        )
    except Exception as e:
        # The challenge is already stored, so a delivery failure would otherwise
        # look like success and strand the user on the code screen.
        log.exception("otp delivery failed")
        raise UpstreamError("Couldn't send the code right now. Try again.") from e

    # Hand the code back only in console/dev mode.
    dev = get_settings().sms_provider == "console"
    return RequestOtpOut(ok=True, dev_code=code if dev else None)


@router.post("/verify-otp", response_model=AuthOut)
def verify_otp(body: VerifyOtpIn, db: Session = Depends(get_session)) -> AuthOut:
    phone = _normalise(body.phone)
    result = verify_code(db, phone, body.code.strip())
    return AuthOut(
        token=issue_token(result.user_id),
        user_id=result.user_id,
        phone=result.phone,
        onboarded=result.onboarded,
    )


@router.post("/device", response_model=AuthOut)
def device_login(
    body: DeviceAuthIn,
    request: Request,
    db: Session = Depends(get_session),
) -> AuthOut:
    """
    Trade a browser-generated device id for a session (create on first use).

    The device id is accepted here and nowhere else — everything downstream uses
    the short-lived token this returns. See `app/auth/device.py` for why.
    """
    client_ip = request.client.host if request.client else "unknown"
    user, _created = device_sign_in(db, body.device_id, client_ip)

    onboarded = db.get(Profile, user.id) is not None
    db.commit()

    return AuthOut(
        token=issue_token(user.id),
        user_id=user.id,
        phone=user.phone,
        onboarded=onboarded,
    )


@router.post("/google", response_model=AuthOut)
async def google_login(
    body: GoogleAuthIn, db: Session = Depends(get_session)
) -> AuthOut:
    """Verify a Google ID token and sign the user in (create on first use)."""
    identity = await verify_id_token(body.id_token)

    user = db.exec(select(User).where(User.google_sub == identity.sub)).first()
    if user is None:
        user = User(google_sub=identity.sub, email=identity.email, name=identity.name)
        db.add(user)
        db.flush()
        log.info("new google user · %s", mask_email(identity.email or ""))
    else:  # keep profile details fresh
        user.email = identity.email or user.email
        user.name = identity.name or user.name
    onboarded = db.get(Profile, user.id) is not None
    db.commit()

    return AuthOut(
        token=issue_token(user.id),
        user_id=user.id,
        phone=user.phone,
        onboarded=onboarded,
    )
