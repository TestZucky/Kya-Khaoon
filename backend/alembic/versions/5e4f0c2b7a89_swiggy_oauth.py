"""swiggy oauth: user token fields + client + auth-flow tables

Revision ID: 5e4f0c2b7a89
Revises: 4d3e9b1a2c56
Create Date: 2026-07-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

revision: str = "5e4f0c2b7a89"
down_revision: Union[str, None] = "4d3e9b1a2c56"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "swiggy_refresh_token", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
    )
    op.add_column(
        "user", sa.Column("swiggy_token_expires_at", sa.DateTime(), nullable=True)
    )
    op.create_table(
        "swiggyoauthclient",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "swiggyauthflow",
        sa.Column("state", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("code_verifier", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("state"),
    )


def downgrade() -> None:
    op.drop_table("swiggyauthflow")
    op.drop_table("swiggyoauthclient")
    op.drop_column("user", "swiggy_token_expires_at")
    op.drop_column("user", "swiggy_refresh_token")
