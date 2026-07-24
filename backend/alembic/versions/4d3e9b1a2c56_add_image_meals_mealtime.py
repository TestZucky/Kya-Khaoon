"""add dishconcept.image_url, dishconcept.meals, session.meal

Revision ID: 4d3e9b1a2c56
Revises: 3c2d8a0f1e34
Create Date: 2026-07-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

revision: str = "4d3e9b1a2c56"
down_revision: Union[str, None] = "3c2d8a0f1e34"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "dishconcept",
        sa.Column(
            "image_url",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "dishconcept",
        sa.Column("meals", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "session",
        sa.Column("meal", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("session", "meal")
    op.drop_column("dishconcept", "meals")
    op.drop_column("dishconcept", "image_url")
