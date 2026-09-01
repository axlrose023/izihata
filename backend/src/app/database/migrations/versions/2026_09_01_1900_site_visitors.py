"""track site visitor activity

Revision ID: a71c4d5e9b02
Revises: e6f32ba8c410
Create Date: 2026-09-01 19:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a71c4d5e9b02"
down_revision: str | None = "e6f32ba8c410"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "site_visitors",
        sa.Column("visitor_key", sa.UUID(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("page_views", sa.Integer(), nullable=False),
        sa.Column("orders_count", sa.Integer(), nullable=False),
        sa.Column("leads_count", sa.Integer(), nullable=False),
        sa.Column("last_path", sa.String(length=500), nullable=True),
        sa.Column("user_agent", sa.String(length=400), nullable=True),
        sa.Column("customer_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=True),
        sa.Column("phone", sa.String(length=24), nullable=True),
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
        sa.CheckConstraint(
            "page_views >= 0",
            name=op.f("site_visitors_site_visitor_page_views_valid_check"),
        ),
        sa.CheckConstraint(
            "orders_count >= 0",
            name=op.f("site_visitors_site_visitor_orders_count_valid_check"),
        ),
        sa.CheckConstraint(
            "leads_count >= 0",
            name=op.f("site_visitors_site_visitor_leads_count_valid_check"),
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name=op.f("site_visitors_customer_id_fkey"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("site_visitors_pkey")),
    )
    op.create_index(
        op.f("site_visitors_visitor_key_idx"),
        "site_visitors",
        ["visitor_key"],
        unique=True,
    )
    op.create_index(
        op.f("site_visitors_customer_id_idx"),
        "site_visitors",
        ["customer_id"],
    )
    op.create_index(op.f("site_visitors_phone_idx"), "site_visitors", ["phone"])
    op.create_index(
        "site_visitors_last_seen_at_idx",
        "site_visitors",
        ["last_seen_at"],
    )


def downgrade() -> None:
    op.drop_index("site_visitors_last_seen_at_idx", table_name="site_visitors")
    op.drop_index(op.f("site_visitors_phone_idx"), table_name="site_visitors")
    op.drop_index(op.f("site_visitors_customer_id_idx"), table_name="site_visitors")
    op.drop_index(op.f("site_visitors_visitor_key_idx"), table_name="site_visitors")
    op.drop_table("site_visitors")
