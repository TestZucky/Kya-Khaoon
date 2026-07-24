"""
Compact signed session tokens — HMAC over a JSON payload, no JWT dependency.

Format:  base64url(payload) + "." + base64url(hmac_sha256(secret, part1))
The payload carries the user id and an expiry; tampering breaks the signature and
an expired token is rejected. Good enough for session auth; swap for a JWT lib if
you later need standard claims or key rotation.
"""

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

from app.config import get_settings


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _sign(part1: str, secret: str) -> str:
    sig = hmac.new(secret.encode(), part1.encode(), hashlib.sha256).digest()
    return _b64e(sig)


def issue_token(user_id: int) -> str:
    s = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(hours=s.session_ttl_hours)
    payload = _b64e(json.dumps({"uid": user_id, "exp": exp.timestamp()}).encode())
    return f"{payload}.{_sign(payload, s.secret_key)}"


def verify_token(token: str) -> int | None:
    """Return the user id for a valid, unexpired token, else None."""
    try:
        payload, sig = token.split(".", 1)
    except ValueError:
        return None
    expected = _sign(payload, get_settings().secret_key)
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        data = json.loads(_b64d(payload))
    except (ValueError, json.JSONDecodeError):
        return None
    if float(data.get("exp", 0)) < datetime.now(timezone.utc).timestamp():
        return None
    return int(data["uid"])
