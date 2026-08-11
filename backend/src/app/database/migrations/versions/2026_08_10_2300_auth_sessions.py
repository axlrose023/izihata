"""add rotating authentication sessions

Revision ID: 3f6a9c0275db
Revises: 7d3d472d0d84
Create Date: 2026-08-10 23:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3f6a9c0275db"
down_revision: str | None = "7d3d472d0d84"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("refresh_jti", sa.UUID(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("auth_sessions_user_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("auth_sessions_pkey")),
        sa.UniqueConstraint(
            "refresh_jti",
            name=op.f("auth_sessions_refresh_jti_ukey"),
        ),
    )
    op.create_index(
        "auth_sessions_expires_at_idx",
        "auth_sessions",
        ["expires_at"],
    )
    op.create_index(
        "auth_sessions_revoked_at_idx",
        "auth_sessions",
        ["revoked_at"],
    )
    op.create_index(
        "auth_sessions_user_id_idx",
        "auth_sessions",
        ["user_id"],
    )
    op.create_index(
        "auth_sessions_user_active_idx",
        "auth_sessions",
        ["user_id", "revoked_at", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index("auth_sessions_user_active_idx", table_name="auth_sessions")
    op.drop_index("auth_sessions_user_id_idx", table_name="auth_sessions")
    op.drop_index("auth_sessions_revoked_at_idx", table_name="auth_sessions")
    op.drop_index("auth_sessions_expires_at_idx", table_name="auth_sessions")
    op.drop_table("auth_sessions")
