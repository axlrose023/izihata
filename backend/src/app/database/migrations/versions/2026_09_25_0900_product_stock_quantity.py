"""add product stock quantity

Revision ID: f5b0c8d2a1e7
Revises: d13a8c4e5f60
Create Date: 2026-09-25 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f5b0c8d2a1e7"
down_revision: str | None = "d13a8c4e5f60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("stock_quantity", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_check_constraint(
        op.f("products_product_stock_quantity_non_negative_check"),
        "products",
        "stock_quantity >= 0",
    )
    op.alter_column("products", "stock_quantity", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        op.f("products_product_stock_quantity_non_negative_check"),
        "products",
        type_="check",
    )
    op.drop_column("products", "stock_quantity")
