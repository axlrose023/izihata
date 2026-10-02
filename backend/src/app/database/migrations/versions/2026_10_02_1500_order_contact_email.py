"""store contact email on orders

Revision ID: e8b65f4a2c17
Revises: 6a72d114ce39
Create Date: 2026-10-02 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e8b65f4a2c17"
down_revision: str | None = "6a72d114ce39"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("email", sa.String(length=254), nullable=True))
    op.execute(
        sa.text(
            "UPDATE orders SET email = "
            "(SELECT customers.email FROM customers "
            "WHERE customers.id = orders.customer_id) "
            "WHERE customer_id IS NOT NULL"
        )
    )


def downgrade() -> None:
    op.drop_column("orders", "email")
