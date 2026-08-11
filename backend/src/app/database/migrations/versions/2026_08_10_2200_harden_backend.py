"""harden backend contracts and operational indexes

Revision ID: 7d3d472d0d84
Revises: f1f04788fce5
Create Date: 2026-08-10 22:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7d3d472d0d84"
down_revision: str | None = "f1f04788fce5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("orders", "customer_note")
    op.create_index("orders_created_at_idx", "orders", ["created_at"])
    op.create_index(
        "ix_outbox_events_dispatch",
        "outbox_events",
        ["status", "next_attempt_at", "locked_until", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_outbox_events_dispatch", table_name="outbox_events")
    op.drop_index("orders_created_at_idx", table_name="orders")
    op.add_column("orders", sa.Column("customer_note", sa.Text(), nullable=True))
