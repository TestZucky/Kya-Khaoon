"""
Swiggy OAuth 2.1 + PKCE + Dynamic Client Registration.

mcp.swiggy.com is a standard remote MCP server — no app to apply for, no secret.
The flow:

  discover  →  register (once)  →  authorize (browser)  →  token  →  refresh

We're a public client (`token_endpoint_auth_method: none`), so PKCE is what proves
the token request came from whoever started the authorize.
"""

import base64
import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from sqlmodel import Session, select

from app.config import get_settings
from app.errors import UpstreamError, ValidationError
from app.models import SwiggyAuthFlow, SwiggyOAuthClient, User

log = logging.getLogger("kya.swiggy")

_SCOPE = "mcp:tools mcp:resources"
_meta_cache: dict | None = None


class SwiggyOAuthError(UpstreamError):
    """Discovery, registration or a token exchange failed."""


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


async def _json(request) -> dict:
    """Await one httpx call, naming every transport/status/parse failure alike."""
    try:
        resp = await request
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        raise SwiggyOAuthError(f"Swiggy returned {e.response.status_code}") from e
    except httpx.HTTPError as e:
        raise SwiggyOAuthError(f"couldn't reach Swiggy: {type(e).__name__}") from e
    except ValueError as e:
        raise SwiggyOAuthError("Swiggy returned an unreadable response") from e


async def _discover() -> dict:
    """OAuth server metadata (RFC 8414), cached for the process lifetime."""
    global _meta_cache
    if _meta_cache is None:
        base = get_settings().swiggy_oauth_base.rstrip("/")
        async with httpx.AsyncClient(timeout=15) as c:
            meta = await _json(c.get(f"{base}/.well-known/oauth-authorization-server"))
        for key in ("authorization_endpoint", "token_endpoint", "registration_endpoint"):
            if key not in meta:
                raise SwiggyOAuthError(f"Swiggy metadata is missing {key}")
        _meta_cache = meta
    return _meta_cache


async def _client_id(db: Session) -> str:
    """Register our client once (RFC 7591) and reuse the id thereafter."""
    row = db.exec(select(SwiggyOAuthClient)).first()
    if row is not None:
        return row.client_id

    meta = await _discover()
    settings = get_settings()
    async with httpx.AsyncClient(timeout=15) as c:
        payload = await _json(
            c.post(
                meta["registration_endpoint"],
                json={
                    "redirect_uris": [settings.swiggy_redirect_uri],
                    "client_name": "Kya Khaoon",
                    "token_endpoint_auth_method": "none",
                    "grant_types": ["authorization_code", "refresh_token"],
                    "response_types": ["code"],
                    "scope": _SCOPE,
                },
            )
        )
    client_id = payload.get("client_id")
    if not client_id:
        raise SwiggyOAuthError("Swiggy registration returned no client_id")

    db.add(SwiggyOAuthClient(client_id=client_id))
    db.commit()
    log.info("registered a new Swiggy OAuth client")
    return client_id


async def start_authorization(db: Session, user_id: int) -> str:
    """Build the authorize URL and stash the PKCE verifier against a state token."""
    meta = await _discover()
    settings = get_settings()
    client_id = await _client_id(db)

    verifier = _b64url(secrets.token_bytes(64))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    state = secrets.token_urlsafe(24)

    db.add(SwiggyAuthFlow(state=state, user_id=user_id, code_verifier=verifier))
    db.commit()

    query = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": settings.swiggy_redirect_uri,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
            "scope": _SCOPE,
        }
    )
    return f"{meta['authorization_endpoint']}?{query}"


@dataclass
class TokenSet:
    access_token: str
    refresh_token: str | None
    expires_at: datetime | None


def _expires_at(payload: dict) -> datetime | None:
    ttl = payload.get("expires_in")
    if not ttl:
        return None
    try:
        return datetime.now(timezone.utc) + timedelta(seconds=int(ttl))
    except (TypeError, ValueError):
        # A missing expiry just means we never pre-emptively refresh.
        return None


async def _post_token(data: dict) -> TokenSet:
    meta = await _discover()
    async with httpx.AsyncClient(timeout=15) as c:
        payload = await _json(c.post(meta["token_endpoint"], data=data))
    access = payload.get("access_token")
    if not access:
        raise SwiggyOAuthError("Swiggy returned no access token")
    return TokenSet(
        access_token=access,
        refresh_token=payload.get("refresh_token"),
        expires_at=_expires_at(payload),
    )


async def complete_callback(db: Session, state: str, code: str) -> int:
    """Exchange the code for tokens, store them on the user, return the user id."""
    flow = db.get(SwiggyAuthFlow, state)
    if flow is None:
        raise ValidationError("unknown or expired auth state")
    settings = get_settings()
    client_id = await _client_id(db)

    tokens = await _post_token(
        {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": flow.code_verifier,
            "redirect_uri": settings.swiggy_redirect_uri,
            "client_id": client_id,
        }
    )

    user = db.get(User, flow.user_id)
    if user is None:
        # The row was deleted between authorize and callback (a wiped dev DB).
        db.delete(flow)
        db.commit()
        raise ValidationError("that account no longer exists — sign in again")
    user.swiggy_token = tokens.access_token
    user.swiggy_refresh_token = tokens.refresh_token
    user.swiggy_token_expires_at = tokens.expires_at
    db.add(user)
    db.delete(flow)
    db.commit()
    return user.id


async def ensure_fresh(db: Session, user: User) -> str | None:
    """
    Return a currently-valid access token for the user, refreshing if it's about
    to expire. Returns None if the user isn't connected.

    A failed refresh is not fatal: we hand back the token we have and let the
    actual Swiggy call decide. Refusing here would break a request that may well
    have succeeded.
    """
    if not user.swiggy_token:
        return None
    exp = user.swiggy_token_expires_at
    if exp is None or not user.swiggy_refresh_token:
        return user.swiggy_token

    exp = exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)
    if exp > datetime.now(timezone.utc) + timedelta(seconds=60):
        return user.swiggy_token

    try:
        client_id = await _client_id(db)
        tokens = await _post_token(
            {
                "grant_type": "refresh_token",
                "refresh_token": user.swiggy_refresh_token,
                "client_id": client_id,
            }
        )
    except SwiggyOAuthError as e:
        log.warning("swiggy token refresh failed for user=%s (%s)", user.id, e)
        return user.swiggy_token

    user.swiggy_token = tokens.access_token
    user.swiggy_refresh_token = tokens.refresh_token or user.swiggy_refresh_token
    user.swiggy_token_expires_at = tokens.expires_at
    db.add(user)
    db.commit()
    log.info("swiggy token refreshed · user=%s", user.id)
    return user.swiggy_token
