"""google identity: nullable phone + google_sub/email/name

Revision ID: 6f5a1d3e8b90
Revises: 5e4f0c2b7a89
Create Date: 2026-07-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

revision: str = "6f5a1d3e8b90"
down_revision: Union[str, None] = "5e4f0c2b7a89"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Batch mode so SQLite (which can't ALTER COLUMN) rebuilds the table.
    with op.batch_alter_table("user") as b:
        b.alter_column("phone", existing_type=sa.String(), nullable=True)
        b.add_column(
            sa.Column("google_sub", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )
        b.add_column(
            sa.Column("email", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )
        b.add_column(
            sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )
        b.create_index("ix_user_google_sub", ["google_sub"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("user") as b:
        b.drop_index("ix_user_google_sub")
        b.drop_column("name")
        b.drop_column("email")
        b.drop_column("google_sub")
        b.alter_column("phone", existing_type=sa.String(), nullable=False)
