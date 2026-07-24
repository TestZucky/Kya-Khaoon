"""add user.swiggy_token

Revision ID: 2a1c7f4e9b02
Revises: 1bb5d0025eaf
Create Date: 2026-07-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

revision: str = "2a1c7f4e9b02"
down_revision: Union[str, None] = "1bb5d0025eaf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("swiggy_token", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user", "swiggy_token")
