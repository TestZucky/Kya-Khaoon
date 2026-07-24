"""encrypt the swiggy credentials already in the database

Data-only: the columns stay unbounded VARCHAR, the bytes in them change. Rows
written from here on encrypt themselves via the EncryptedString column type —
this is purely for the rows that predate it.

Idempotent in both directions (it skips anything already in the target state),
so a re-run or a partial run costs nothing.

Revision ID: b2e7f1a4c806
Revises: 9c8d4e6f1a23
Create Date: 2026-07-24
"""
from typing import Callable, Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.crypto import decrypt, encrypt, is_encrypted

revision: str = "b2e7f1a4c806"
down_revision: Union[str, None] = "9c8d4e6f1a23"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# table, primary key, the credential columns in it
_TARGETS = (
    ("user", "id", ("swiggy_token", "swiggy_refresh_token")),
    ("swiggyauthflow", "state", ("code_verifier",)),
)


def _rewrite(transform: Callable[[str], str | None]) -> None:
    """Apply `transform` to every credential column; None means leave it alone.

    Deliberately raw SQL rather than the ORM: the models now carry the encrypting
    column type, so reading through them would decrypt on the way in and defeat
    the whole exercise.
    """
    conn = op.get_bind()
    for table, pk, columns in _TARGETS:
        selected = ", ".join(f'"{c}"' for c in columns)
        rows = conn.execute(sa.text(f'SELECT "{pk}", {selected} FROM "{table}"')).fetchall()
        for row in rows:
            updates = {}
            for offset, column in enumerate(columns, start=1):
                value = row[offset]
                if value is None:
                    continue
                new = transform(value)
                if new is not None:
                    updates[column] = new
            if not updates:
                continue
            assignments = ", ".join(f'"{c}" = :{c}' for c in updates)
            conn.execute(
                sa.text(f'UPDATE "{table}" SET {assignments} WHERE "{pk}" = :pk'),
                {**updates, "pk": row[0]},
            )


def upgrade() -> None:
    _rewrite(lambda v: None if is_encrypted(v) else encrypt(v))


def downgrade() -> None:
    _rewrite(lambda v: decrypt(v) if is_encrypted(v) else None)
