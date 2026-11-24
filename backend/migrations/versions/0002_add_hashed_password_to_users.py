"""add hashed_password to users

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-23 19:46:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "hashed_password",
            sa.String(length=255),
            nullable=False,
            server_default="",
        ),
    )
    # Remove server_default so future rows must supply it
    op.alter_column("users", "hashed_password", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "hashed_password")
