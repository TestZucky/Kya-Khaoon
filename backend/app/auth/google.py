"""
Google Sign-In — verify the ID token the browser gets from Google Identity
Services.

Verification goes through Google's `tokeninfo` endpoint, which checks the
signature and expiry server-side and returns the claims. We then confirm the
audience is *our* client id (so a token minted for another app can't be replayed
here) and that the issuer is Google.
"""

import logging
from dataclasses import dataclass

import httpx

from app.config import get_settings
from app.errors import AuthError, UpstreamError

log = logging.getLogger("kya.auth")

_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


class GoogleAuthError(AuthError):
    """The token isn't one we'll accept. Never says why in detail — that's a hint."""


@dataclass
class GoogleIdentity:
    sub: str
    email: str | None
    name: str | None


async def verify_id_token(id_token: str) -> GoogleIdentity:
    settings = get_settings()
    if not settings.google_client_id:
        raise GoogleAuthError("Google sign-in isn't configured (no GOOGLE_CLIENT_ID)")

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(_TOKENINFO_URL, params={"id_token": id_token})
    except httpx.HTTPError as e:
        # Google unreachable is our problem, not a bad credential — a 401 here
        # would log the user out for what is really an outage.
        log.warning("google tokeninfo unreachable: %s", type(e).__name__)
        raise UpstreamError("Couldn't reach Google to verify your sign-in.") from e

    if resp.status_code != 200:
        raise GoogleAuthError("invalid Google token")

    try:
        claims = resp.json()
    except ValueError as e:
        raise UpstreamError("Google returned an unreadable response.") from e

    if claims.get("aud") != settings.google_client_id:
        raise GoogleAuthError("token was not issued for this app")
    if claims.get("iss") not in _ISSUERS:
        raise GoogleAuthError("unexpected token issuer")
    sub = claims.get("sub")
    if not sub:
        raise GoogleAuthError("token missing subject")

    return GoogleIdentity(sub=sub, email=claims.get("email"), name=claims.get("name"))
