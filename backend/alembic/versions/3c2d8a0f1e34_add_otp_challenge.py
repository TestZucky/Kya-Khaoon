"""add otpchallenge table

Revision ID: 3c2d8a0f1e34
Revises: 2a1c7f4e9b02
Create Date: 2026-07-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

revision: str = "3c2d8a0f1e34"
down_revision: Union[str, None] = "2a1c7f4e9b02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "otpchallenge",
        sa.Column("phone", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("code_hash", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_sent_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("phone"),
    )


def downgrade() -> None:
    op.drop_table("otpchallenge")
