"""Persist payment attempts and their provider references."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d77f8ef34d11"
down_revision: str | None = "b3a9ef720c16"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payment_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column(
            "provider",
            sa.String(length=32),
            server_default="wayforpay",
            nullable=False,
        ),
        sa.Column("order_reference", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "currency", sa.String(length=3), server_default="UAH", nullable=False
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "paid",
                "failed",
                "refunded",
                name="paymentattemptstatus",
                native_enum=False,
                length=24,
            ),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.current_timestamp(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.current_timestamp(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_reference"),
    )
    op.create_index("payment_attempts_order_id_idx", "payment_attempts", ["order_id"])


def downgrade() -> None:
    op.drop_index("payment_attempts_order_id_idx", table_name="payment_attempts")
    op.drop_table("payment_attempts")
