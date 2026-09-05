"""mark products as editorially popular

Revision ID: c92f7b6d1a34
Revises: a71c4d5e9b02
Create Date: 2026-09-05 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c92f7b6d1a34"
down_revision: str | None = "a71c4d5e9b02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column(
            "is_popular",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    # Seed the flag from the existing "hit" badge so the storefront keeps a
    # populated block, then let staff curate it independently.
    op.execute("UPDATE products SET is_popular = true WHERE badge = 'TOP'")
    op.alter_column("products", "is_popular", server_default=None)
    op.create_index(op.f("products_is_popular_idx"), "products", ["is_popular"])


def downgrade() -> None:
    op.drop_index(op.f("products_is_popular_idx"), table_name="products")
    op.drop_column("products", "is_popular")
