"""keycloak_users

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-26 20:58:07.480032

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: str | Sequence[str] | None = '0003'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Keycloak пайдаланушыларына көшу (3 қадамдық қауіпсіз миграция)."""
    # 1-қадам: keycloak_id бағанын уақытша nullable=True етіп қосу
    op.add_column(
        "users", sa.Column("keycloak_id", sa.String(length=64), nullable=True)
    )
    # 2-қадам: бар legacy-жазбаларды уақытша бірегей мәнмен толтыру
    op.execute(
        "UPDATE users SET keycloak_id = 'legacy-' || id::text "
        "WHERE keycloak_id IS NULL"
    )
    # 3-қадам: NOT NULL шектеуі, бірегей индекс және hashed_password-ты жою
    op.alter_column(
        "users",
        "keycloak_id",
        existing_type=sa.String(length=64),
        nullable=False,
    )
    op.create_index(
        op.f("ix_users_keycloak_id"), "users", ["keycloak_id"], unique=True
    )
    op.drop_column("users", "hashed_password")


def downgrade() -> None:
    """Алдыңғы сұлбаға қайтару."""
    op.add_column(
        "users",
        sa.Column(
            "hashed_password",
            sa.VARCHAR(length=255),
            autoincrement=False,
            nullable=False,
            server_default="",
        ),
    )
    op.alter_column("users", "hashed_password", server_default=None)
    op.drop_index(op.f("ix_users_keycloak_id"), table_name="users")
    op.drop_column("users", "keycloak_id")
