"""
OTP generation and verification.

The code is never stored in the clear — only sha256(phone + code). A code lives
for a few minutes, survives a few wrong tries, and can't be re-requested faster
than the resend interval. Verification is where the user record is ensured
(get-or-create by phone).
"""

import hashlib
import hmac
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.config import get_settings
from app.errors import RateLimitError, ValidationError
from app.logging_config import mask_phone
from app.models import OtpChallenge, Profile, User

log = logging.getLogger("kya.otp")


class OtpError(ValidationError):
    """A bad or expired code. The message is safe to show the user verbatim."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash(phone: str, code: str) -> str:
    return hashlib.sha256(f"{phone}:{code}".encode()).hexdigest()


def _as_aware(dt: datetime) -> datetime:
    # These columns are TIMESTAMP WITHOUT TIME ZONE, so Postgres hands the value
    # back naive. Everything is stored as UTC — say so explicitly before comparing.
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def request_code(db: Session, phone: str) -> str:
    """Create/refresh a challenge for this phone and return the plaintext code."""
    s = get_settings()
    existing = db.get(OtpChallenge, phone)
    if existing is not None:
        since = (_now() - _as_aware(existing.last_sent_at)).total_seconds()
        if since < s.otp_resend_interval_seconds:
            wait = int(s.otp_resend_interval_seconds - since)
            raise RateLimitError(f"Please wait {wait}s before requesting another code.")

    code = "".join(secrets.choice("0123456789") for _ in range(s.otp_length))
    challenge = existing or OtpChallenge(phone=phone, code_hash="", expires_at=_now())
    challenge.code_hash = _hash(phone, code)
    challenge.expires_at = _now() + timedelta(seconds=s.otp_ttl_seconds)
    challenge.attempts = 0
    challenge.last_sent_at = _now()
    db.add(challenge)
    db.commit()
    log.info("otp issued for %s", mask_phone(phone))
    return code


@dataclass
class VerifiedUser:
    user_id: int
    phone: str
    onboarded: bool


def verify_code(db: Session, phone: str, code: str) -> VerifiedUser:
    s = get_settings()
    challenge = db.get(OtpChallenge, phone)
    if challenge is None:
        raise OtpError("Request a code first.")
    if _as_aware(challenge.expires_at) < _now():
        db.delete(challenge)
        db.commit()
        raise OtpError("That code has expired — request a new one.")

    if challenge.attempts >= s.otp_max_attempts:
        db.delete(challenge)
        db.commit()
        raise RateLimitError("Too many wrong attempts — request a new code.")

    if not hmac.compare_digest(challenge.code_hash, _hash(phone, code)):
        challenge.attempts += 1
        db.add(challenge)
        db.commit()
        left = s.otp_max_attempts - challenge.attempts
        log.info("otp mismatch for %s · %d attempt(s) left", mask_phone(phone), left)
        raise OtpError(f"Incorrect code. {left} attempt(s) left.")

    # Correct — burn the challenge and ensure the user exists.
    db.delete(challenge)
    user = db.exec(select(User).where(User.phone == phone)).first()
    if user is None:
        user = User(phone=phone)
        db.add(user)
        db.flush()
    onboarded = db.get(Profile, user.id) is not None
    db.commit()
    log.info("otp verified · user=%s", user.id)
    return VerifiedUser(user_id=user.id, phone=phone, onboarded=onboarded)
