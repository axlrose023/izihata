"""cover distinct product counts in specification facets

Revision ID: 4c92a8e17b60
Revises: e8b65f4a2c17
"""

from collections.abc import Sequence

from alembic import op

revision: str = "4c92a8e17b60"
down_revision: str | None = "e8b65f4a2c17"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    # Build the replacement before removing the old index, without blocking
    # product imports or staff writes while PostgreSQL scans the attributes.
    with op.get_context().autocommit_block():
        op.create_index(
            "product_attributes_facet_idx",
            "product_attributes",
            ["key", "value", "product_id"],
            postgresql_concurrently=True,
        )
        op.drop_index("product_attributes_key_value_idx", postgresql_concurrently=True)


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.create_index(
            "product_attributes_key_value_idx",
            "product_attributes",
            ["key", "value"],
            postgresql_concurrently=True,
        )
        op.drop_index("product_attributes_facet_idx", postgresql_concurrently=True)
