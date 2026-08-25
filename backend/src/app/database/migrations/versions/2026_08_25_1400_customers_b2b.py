"""add customer accounts and B2B companies

Revision ID: e6f32ba8c410
Revises: d4e2178cba92
Create Date: 2026-08-25 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e6f32ba8c410"
down_revision: str | None = "d4e2178cba92"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=128), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=24), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("customers_pkey")),
    )
    op.create_index(op.f("customers_email_idx"), "customers", ["email"], unique=True)
    op.create_table(
        "customer_auth_sessions",
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("refresh_jti", sa.UUID(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name=op.f("customer_auth_sessions_customer_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("customer_auth_sessions_pkey")),
        sa.UniqueConstraint(
            "refresh_jti",
            name=op.f("customer_auth_sessions_refresh_jti_ukey"),
        ),
    )
    op.create_index(
        op.f("customer_auth_sessions_customer_id_idx"),
        "customer_auth_sessions",
        ["customer_id"],
    )
    op.create_index(
        op.f("customer_auth_sessions_expires_at_idx"),
        "customer_auth_sessions",
        ["expires_at"],
    )
    op.create_index(
        op.f("customer_auth_sessions_revoked_at_idx"),
        "customer_auth_sessions",
        ["revoked_at"],
    )
    op.create_index(
        "customer_auth_sessions_customer_active_idx",
        "customer_auth_sessions",
        ["customer_id", "revoked_at", "expires_at"],
    )
    op.create_table(
        "customer_companies",
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "FOP",
                "LEGAL_ENTITY",
                name="companykind",
                native_enum=False,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("edrpou", sa.String(length=10), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "APPROVED",
                "REJECTED",
                name="companystatus",
                native_enum=False,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("manager_name", sa.String(length=120), nullable=True),
        sa.Column(
            "cumulative_discount_rate",
            sa.Numeric(precision=5, scale=4),
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
        sa.CheckConstraint(
            "cumulative_discount_rate >= 0 AND cumulative_discount_rate < 1",
            name=op.f(
                "customer_companies_customer_company_cumulative_discount_range_check"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name=op.f("customer_companies_customer_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("customer_companies_pkey")),
        sa.UniqueConstraint(
            "customer_id",
            name=op.f("customer_companies_customer_id_ukey"),
        ),
    )
    op.create_index(
        op.f("customer_companies_customer_id_idx"),
        "customer_companies",
        ["customer_id"],
    )
    op.create_index(
        op.f("customer_companies_edrpou_idx"),
        "customer_companies",
        ["edrpou"],
        unique=True,
    )
    op.create_index(
        op.f("customer_companies_status_idx"),
        "customer_companies",
        ["status"],
    )
    op.add_column("orders", sa.Column("customer_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f("orders_customer_id_fkey"),
        "orders",
        "customers",
        ["customer_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("orders_customer_id_idx"), "orders", ["customer_id"])


def downgrade() -> None:
    op.drop_index(op.f("orders_customer_id_idx"), table_name="orders")
    op.drop_constraint(op.f("orders_customer_id_fkey"), "orders", type_="foreignkey")
    op.drop_column("orders", "customer_id")
    op.drop_index(
        op.f("customer_companies_status_idx"), table_name="customer_companies"
    )
    op.drop_index(
        op.f("customer_companies_edrpou_idx"), table_name="customer_companies"
    )
    op.drop_index(
        op.f("customer_companies_customer_id_idx"),
        table_name="customer_companies",
    )
    op.drop_table("customer_companies")
    op.drop_index(
        "customer_auth_sessions_customer_active_idx",
        table_name="customer_auth_sessions",
    )
    op.drop_index(
        op.f("customer_auth_sessions_revoked_at_idx"),
        table_name="customer_auth_sessions",
    )
    op.drop_index(
        op.f("customer_auth_sessions_expires_at_idx"),
        table_name="customer_auth_sessions",
    )
    op.drop_index(
        op.f("customer_auth_sessions_customer_id_idx"),
        table_name="customer_auth_sessions",
    )
    op.drop_table("customer_auth_sessions")
    op.drop_index(op.f("customers_email_idx"), table_name="customers")
    op.drop_table("customers")
