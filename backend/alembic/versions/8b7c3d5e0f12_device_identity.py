"""device identity: nullable device_id on user

Revision ID: 8b7c3d5e0f12
Revises: 7a6b2c4d9e01
Create Date: 2026-07-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

revision: str = "8b7c3d5e0f12"
down_revision: Union[str, None] = "7a6b2c4d9e01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable + unique, alongside phone and google_sub: existing users keep NULL
    # and stay reachable by whichever identifier they signed up with.
    with op.batch_alter_table("user") as b:
        b.add_column(
            sa.Column("device_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )
        b.create_index("ix_user_device_id", ["device_id"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("user") as b:
        b.drop_index("ix_user_device_id")
        b.drop_column("device_id")
