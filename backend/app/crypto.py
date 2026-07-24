"""
Encryption at rest for the credentials we hold on a user's behalf.

A user's Swiggy tokens are not ours: the access token acts as them on Swiggy,
and the refresh token mints new access tokens more or less forever. Crucially,
they carry *Swiggy's* permissions, not the subset this app chooses to use — a
stolen token could place an order even though no code here ever calls
`place_food_order`. So they don't sit in the database as readable text.

The key lives outside the database (env, or a secret manager in production),
which is the whole point: a leaked dump, backup or disk snapshot is inert on its
own. This does not defend against someone on the running host — the app needs
the key to work — it defends against the database-shaped leaks that actually
happen.

`EncryptedString` is a column type, so callers never see any of this. Assigning
`user.swiggy_token = "..."` and reading it back behaves exactly as before; only
what lands on disk changes.
"""

import base64
import hashlib
import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

from app.config import get_settings

log = logging.getLogger("kya.crypto")


def _derived_key(secret: str) -> str:
    """A Fernet key from `secret_key`, for when no explicit key is configured.

    Keeps dev and CI to a single secret to manage. Production should set
    TOKEN_ENCRYPTION_KEY so that rotating the session-signing key doesn't also
    invalidate every stored Swiggy connection.
    """
    digest = hashlib.sha256(f"kya-token-encryption-v1:{secret}".encode()).digest()
    return base64.urlsafe_b64encode(digest).decode()


@lru_cache
def _cipher() -> MultiFernet:
    """
    Built once per process. TOKEN_ENCRYPTION_KEY may hold several comma-separated
    keys: the first encrypts, any of them can decrypt. That's what makes rotation
    possible without disconnecting everyone — add the new key at the front, let
    writes re-encrypt, drop the old one later.
    """
    settings = get_settings()
    keys = [k.strip() for k in settings.token_encryption_key.split(",") if k.strip()]
    if not keys:
        keys = [_derived_key(settings.secret_key)]
    try:
        return MultiFernet([Fernet(k) for k in keys])
    except (ValueError, TypeError) as e:
        raise RuntimeError(
            "TOKEN_ENCRYPTION_KEY must be url-safe base64 of 32 bytes — generate one "
            "with: python -c 'from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())'"
        ) from e


def encrypt(value: str) -> str:
    return _cipher().encrypt(value.encode()).decode()


def decrypt(value: str) -> str | None:
    """
    Plaintext, or None if this ciphertext can't be read with the keys we have.

    None rather than an exception: an unreadable token means the key changed (or
    the row predates encryption), and the honest consequence is that the user
    looks disconnected and reconnects. Raising here would instead break every
    request for that user, including the ones that would let them fix it.
    """
    try:
        return _cipher().decrypt(value.encode()).decode()
    except (InvalidToken, ValueError):
        log.warning("could not decrypt a stored credential — treating it as absent")
        return None


def is_encrypted(value: str) -> bool:
    """Whether we could read this back. Used by the migration to stay idempotent."""
    try:
        _cipher().decrypt(value.encode())
        return True
    except (InvalidToken, ValueError):
        return False


class EncryptedString(TypeDecorator):
    """A VARCHAR column whose value is encrypted on the way in and out.

    `impl = String` means the underlying column is the same unbounded VARCHAR it
    always was — this changes the bytes stored, never the schema.
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        return None if value is None else encrypt(value)

    def process_result_value(self, value: str | None, dialect) -> str | None:
        return None if value is None else decrypt(value)
