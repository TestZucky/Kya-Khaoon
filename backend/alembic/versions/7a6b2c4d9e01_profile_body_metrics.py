"""profile body metrics: height_cm, weight_kg, home_state

Revision ID: 7a6b2c4d9e01
Revises: 6f5a1d3e8b90
Create Date: 2026-07-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

revision: str = "7a6b2c4d9e01"
down_revision: Union[str, None] = "6f5a1d3e8b90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # All nullable — existing profiles (and users who skip these steps) keep NULL.
    with op.batch_alter_table("profile") as b:
        b.add_column(sa.Column("height_cm", sa.Integer(), nullable=True))
        b.add_column(sa.Column("weight_kg", sa.Integer(), nullable=True))
        b.add_column(
            sa.Column("home_state", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("profile") as b:
        b.drop_column("home_state")
        b.drop_column("weight_kg")
        b.drop_column("height_cm")
