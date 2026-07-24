import logging

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from app.auth.deps import current_user
from app.config import get_settings
from app.db import get_session
from app.errors import AppError, UpstreamError
from app.models import User
from app.swiggy import oauth

router = APIRouter(prefix="/auth/swiggy", tags=["swiggy-auth"])
log = logging.getLogger("kya.swiggy")


@router.get("/status")
def status(user: User = Depends(current_user)) -> dict[str, bool]:
    return {"connected": bool(user.swiggy_token)}


@router.post("/start")
async def start(
    user: User = Depends(current_user),
    db: Session = Depends(get_session),
) -> dict[str, str]:
    """Return the Swiggy authorize URL for the frontend to redirect the user to."""
    try:
        url = await oauth.start_authorization(db, user.id)
    except AppError:
        raise
    except Exception as e:
        log.exception("swiggy authorize start failed · user=%s", user.id)
        raise UpstreamError("Couldn't start the Swiggy connection.") from e
    return {"authorize_url": url}


@router.get("/callback")
async def callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_session),
) -> RedirectResponse:
    """
    Swiggy redirects here after the user authorizes, then we bounce to the app.

    Every failure ends as a redirect rather than a JSON error: the user is in a
    browser mid-flow, so a raw 502 body would be a dead end. `/connect` reads the
    query flag and routes onward based on where they are in setup.
    """
    front = get_settings().frontend_url.rstrip("/")
    if error or not (code and state):
        log.warning("swiggy callback rejected · provider_error=%s", bool(error))
        return RedirectResponse(f"{front}/connect?swiggy=error")
    try:
        user_id = await oauth.complete_callback(db, state, code)
    except AppError as e:
        # A stale or replayed state — expected, and not worth a stack trace.
        log.warning("swiggy callback rejected: %s", e.message)
        return RedirectResponse(f"{front}/connect?swiggy=error")
    except Exception:
        log.exception("swiggy callback exchange failed")
        return RedirectResponse(f"{front}/connect?swiggy=error")
    log.info("swiggy connected · user=%s", user_id)
    return RedirectResponse(f"{front}/connect?swiggy=connected")
