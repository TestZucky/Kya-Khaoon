"""
Device-id sign-in: the browser generates a UUID, keeps it in localStorage, and
trades it for a session token here.

This is *persistence*, not identity — it reliably remembers a browser and knows
nothing about the person using it. Two things follow, and both are enforced below:

1. The device id never expires and can't be rotated, so it is accepted **only**
   here. Every other endpoint takes the short-lived signed token from
   `auth.tokens`, which is what limits the damage if a device id leaks.
2. This endpoint creates rows without verifying anything, and a fresh user can
   trigger a paid LLM deck generation. So it's rate-limited per client IP —
   otherwise a for-loop runs up the OpenAI bill and fills the table with junk.

The limiter is a per-process in-memory window: it resets on restart and doesn't
span workers. That's honest for a single-uvicorn demo; a real deployment wants
Redis.
"""

import logging
from collections import deque
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.config import get_settings
from app.errors import RateLimitError, ValidationError
from app.models import User

log = logging.getLogger("kya.auth")

# Accepted shape for a client-generated id — crypto.randomUUID() is 36 chars. We
# don't require a strict UUID (any opaque token works), just something long
# enough not to be guessable and short enough not to be a payload.
_MIN_LEN = 16
_MAX_LEN = 128

# client ip -> timestamps of recent mints, oldest first.
_recent: dict[str, deque[float]] = {}


def _now() -> float:
    return datetime.now(timezone.utc).timestamp()


def _check_rate_limit(client_ip: str) -> None:
    s = get_settings()
    window, limit = s.device_signup_window_seconds, s.device_signup_max_per_window
    cutoff = _now() - window
    hits = _recent.setdefault(client_ip, deque())
    while hits and hits[0] < cutoff:
        hits.popleft()
    if len(hits) >= limit:
        log.warning("device sign-up rate limit hit (%d in %ds)", limit, window)
        raise RateLimitError("Too many sign-ups from this device. Try again later.")
    hits.append(_now())


def sign_in(db: Session, device_id: str, client_ip: str) -> tuple[User, bool]:
    """
    Get-or-create the user behind `device_id`. Returns (user, created).

    Only *creating* a user is rate-limited — a returning device gets its session
    back no matter how often it asks, so a busy user is never locked out.
    """
    device_id = device_id.strip()
    if not (_MIN_LEN <= len(device_id) <= _MAX_LEN):
        raise ValidationError("invalid device id", status_code=422)

    user = db.exec(select(User).where(User.device_id == device_id)).first()
    if user is not None:
        return user, False

    _check_rate_limit(client_ip)
    user = User(device_id=device_id)
    db.add(user)
    db.flush()  # assign the id; the caller commits
    log.info("new device user created · user=%s", user.id)
    return user, True


def reset_rate_limits() -> None:
    """Test hook — the limiter is process-global."""
    _recent.clear()
