"""add custom board requests and portfolio

Revision ID: d4e2178cba92
Revises: a8d13c9be721
Create Date: 2026-08-25 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e2178cba92"
down_revision: str | None = "a8d13c9be721"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "custom_board_portfolio_items",
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("custom_board_portfolio_items_pkey")),
    )
    op.create_table(
        "custom_board_requests",
        sa.Column("customer_name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=24), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column(
            "application",
            sa.Enum(
                "APARTMENT",
                "HOUSE",
                "INDUSTRIAL",
                name="boardapplication",
                native_enum=False,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("groups_count", sa.Integer(), nullable=False),
        sa.Column("ip_class", sa.String(length=16), nullable=False),
        sa.Column("automation_brand", sa.String(length=120), nullable=True),
        sa.Column("budget", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column(
            "estimated_from_price",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "NEW",
                "IN_PROGRESS",
                "QUOTED",
                "CLOSED",
                "CANCELLED",
                name="boardrequeststatus",
                native_enum=False,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("custom_board_requests_pkey")),
    )
    op.create_index(
        op.f("custom_board_requests_phone_idx"),
        "custom_board_requests",
        ["phone"],
    )
    op.create_index(
        op.f("custom_board_requests_status_idx"),
        "custom_board_requests",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("custom_board_requests_status_idx"),
        table_name="custom_board_requests",
    )
    op.drop_index(
        op.f("custom_board_requests_phone_idx"),
        table_name="custom_board_requests",
    )
    op.drop_table("custom_board_requests")
    op.drop_table("custom_board_portfolio_items")
