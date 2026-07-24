"""profile spice_level: heat tolerance, 0..4

Revision ID: 9c8d4e6f1a23
Revises: 8b7c3d5e0f12
Create Date: 2026-07-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "9c8d4e6f1a23"
down_revision: Union[str, None] = "8b7c3d5e0f12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing profiles get 2 (medium) — the same default new profiles use, so
    # nobody's picks shift just because the column appeared.
    with op.batch_alter_table("profile") as b:
        b.add_column(
            sa.Column("spice_level", sa.Integer(), nullable=False, server_default="2")
        )


def downgrade() -> None:
    with op.batch_alter_table("profile") as b:
        b.drop_column("spice_level")
