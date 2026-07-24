"""FastAPI dependency that turns a Bearer session token into the current user."""

from fastapi import Depends, Header
from sqlmodel import Session

from app.auth.tokens import verify_token
from app.db import get_session
from app.errors import AuthError
from app.models import User


def current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_session),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError("missing bearer token")
    user_id = verify_token(authorization.split(" ", 1)[1].strip())
    if user_id is None:
        raise AuthError("invalid or expired token")
    user = db.get(User, user_id)
    if user is None:
        # The token was valid but its row is gone (wiped DB). The client re-mints
        # from its device id on a 401, so this heals itself.
        raise AuthError("user no longer exists")
    return user
