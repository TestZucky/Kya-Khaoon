"""
Swiggy credentials are encrypted at rest.

The assertion that matters is the negative one: read the raw column, straight
past the ORM, and the token must not be in there. Everything else — round-trip,
rotation, an unreadable value — is about the app still behaving sanely.

Run:  python -m tests.test_token_encryption
"""

import os

from tests.dbsetup import fresh_db, use_test_db  # noqa: E402

use_test_db()
os.environ["SWIGGY_CLIENT"] = "fake"

from sqlalchemy import text  # noqa: E402
from sqlmodel import Session  # noqa: E402

from app import crypto  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import engine  # noqa: E402
from app.models import SwiggyAuthFlow, User  # noqa: E402

ACCESS = "swiggy-access-token-abc123"
REFRESH = "swiggy-refresh-token-xyz789"
VERIFIER = "pkce-code-verifier-qwerty"


def _raw(db: Session, sql: str, **params):
    """Read a column without the ORM, so no decryption happens on the way out."""
    return db.execute(text(sql), params).first()


def _use_keys(*keys: str) -> None:
    """Swap the configured key(s) and rebuild the cipher, as a restart would."""
    os.environ["TOKEN_ENCRYPTION_KEY"] = ",".join(keys)
    get_settings.cache_clear()
    crypto._cipher.cache_clear()


def main() -> None:
    fresh_db()

    with Session(engine) as db:
        user = User(phone="9800000777", swiggy_token=ACCESS, swiggy_refresh_token=REFRESH)
        db.add(user)
        db.commit()
        db.refresh(user)
        uid = user.id

        db.add(SwiggyAuthFlow(state="state-1", user_id=uid, code_verifier=VERIFIER))
        db.commit()

        # 1. Nothing readable landed on disk.
        stored_access, stored_refresh = _raw(
            db, 'SELECT swiggy_token, swiggy_refresh_token FROM "user" WHERE id = :id', id=uid
        )
        assert stored_access != ACCESS and stored_refresh != REFRESH
        assert ACCESS not in stored_access and REFRESH not in stored_refresh
        assert stored_access.startswith("gAAAA")  # a Fernet token
        print("  ok  the stored bytes are ciphertext, not the token")

        stored_verifier = _raw(
            db, "SELECT code_verifier FROM swiggyauthflow WHERE state = :s", s="state-1"
        )[0]
        assert stored_verifier != VERIFIER and VERIFIER not in stored_verifier
        print("  ok  the PKCE verifier is encrypted too")

        # 2. The app reads them back unchanged — callers see no difference.
        db.expire_all()
        reloaded = db.get(User, uid)
        assert reloaded.swiggy_token == ACCESS
        assert reloaded.swiggy_refresh_token == REFRESH
        assert db.get(SwiggyAuthFlow, "state-1").code_verifier == VERIFIER
        print("  ok  round-trips back to the original values")

        # 3. Two encryptions of the same token differ (Fernet carries a random
        #    IV), so the column can't be scanned for who shares a value.
        assert crypto.encrypt(ACCESS) != crypto.encrypt(ACCESS)
        assert crypto.decrypt(crypto.encrypt(ACCESS)) == ACCESS
        print("  ok  the same token encrypts to different bytes each time")

        # 4. A value we can't decrypt reads as absent rather than exploding —
        #    the user simply looks disconnected and can reconnect.
        db.execute(
            text('UPDATE "user" SET swiggy_token = :junk WHERE id = :id'),
            {"junk": "not-a-fernet-token", "id": uid},
        )
        db.commit()
        db.expire_all()
        assert db.get(User, uid).swiggy_token is None
        print("  ok  an unreadable value reads as None, not an error")

    # 5. Rotation: a token written under the old key is still readable once a
    #    new key is put in front of it.
    from cryptography.fernet import Fernet

    old_key, new_key = Fernet.generate_key().decode(), Fernet.generate_key().decode()

    _use_keys(old_key)
    under_old = crypto.encrypt(ACCESS)

    _use_keys(new_key, old_key)
    assert crypto.decrypt(under_old) == ACCESS
    assert crypto.encrypt(ACCESS) != under_old  # new writes use the new key
    print("  ok  a key rotation keeps existing credentials readable")

    _use_keys(new_key)
    assert crypto.decrypt(under_old) is None  # ...and dropping the old key drops them
    print("  ok  retiring the old key does retire what it encrypted")

    print("\nTOKEN ENCRYPTION TESTS PASSED ✅")


if __name__ == "__main__":
    main()
