"""index case-insensitive exact manufacturer SKU search

Revision ID: 2f41d980ca73
Revises: 4c92a8e17b60
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2f41d980ca73"
down_revision: str | None = "4c92a8e17b60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.create_index(
            "products_sku_lower_idx",
            "products",
            [sa.text("lower(sku)")],
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index("products_sku_lower_idx", postgresql_concurrently=True)
