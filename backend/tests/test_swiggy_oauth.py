"""
Swiggy OAuth logic — the parts that don't need a real browser login.

The authorize step (user logs into Swiggy, taps Allow) can only be tested live,
so here we mock discovery / client-id / token-exchange and prove: the authorize
URL is built correctly with PKCE, and the callback stores the tokens on the user.

Run:  python -m tests.test_swiggy_oauth
"""

import asyncio
import os
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

os.environ.setdefault("DATABASE_URL", "sqlite:///./oauth_test.db")
os.environ["SWIGGY_CLIENT"] = "fake"

from sqlmodel import Session, select  # noqa: E402

from app.db import engine, init_db  # noqa: E402
from app.models import SwiggyAuthFlow, User  # noqa: E402
from app.swiggy import oauth  # noqa: E402

FAKE_META = {
    "authorization_endpoint": "https://mcp.swiggy.com/auth/authorize",
    "token_endpoint": "https://mcp.swiggy.com/auth/token",
    "registration_endpoint": "https://mcp.swiggy.com/auth/register",
}


async def _fake_discover():
    return FAKE_META


async def _fake_client_id(_db):
    return "swiggy-mcp"


def main() -> None:
    init_db()
    # Patch the network calls; keep the real PKCE + URL logic.
    oauth._discover = _fake_discover  # type: ignore[assignment]
    oauth._client_id = _fake_client_id  # type: ignore[assignment]

    with Session(engine) as db:
        user = User(phone="9800000123")
        db.add(user)
        db.commit()
        db.refresh(user)
        uid = user.id

        # 1. start → a proper authorize URL + a stored flow.
        url = asyncio.run(oauth.start_authorization(db, uid))
        q = parse_qs(urlparse(url).query)
        assert url.startswith("https://mcp.swiggy.com/auth/authorize?")
        assert q["client_id"] == ["swiggy-mcp"]
        assert q["response_type"] == ["code"]
        assert q["code_challenge_method"] == ["S256"]
        assert q["code_challenge"] and q["state"]
        assert "mcp:tools" in q["scope"][0]
        print("  ok  authorize URL built with PKCE challenge + state")

        flow = db.exec(select(SwiggyAuthFlow)).first()
        assert flow and flow.user_id == uid
        state = flow.state
        print("  ok  pending auth-flow stored against the user")

        # 2. callback → tokens land on the user, flow is consumed.
        async def _fake_post_token(data):
            assert data["grant_type"] == "authorization_code"
            assert data["code"] == "the-code"
            assert data["code_verifier"] == flow.code_verifier
            return oauth.TokenSet(
                access_token="acc-123",
                refresh_token="ref-456",
                expires_at=datetime.now(timezone.utc),
            )

        oauth._post_token = _fake_post_token  # type: ignore[assignment]
        returned_uid = asyncio.run(oauth.complete_callback(db, state, "the-code"))
        assert returned_uid == uid

        db.refresh(user)
        assert user.swiggy_token == "acc-123"
        assert user.swiggy_refresh_token == "ref-456"
        assert db.exec(select(SwiggyAuthFlow)).first() is None  # consumed
        print("  ok  callback exchanged code → stored tokens, flow consumed")

    print("\nSWIGGY OAUTH TESTS PASSED ✅")
    if os.path.exists("./oauth_test.db"):
        os.remove("./oauth_test.db")


if __name__ == "__main__":
    main()
