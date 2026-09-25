"""preserve product characteristic source and order

Revision ID: a6e4d5f7092b
Revises: f5b0c8d2a1e7
Create Date: 2026-09-25 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a6e4d5f7092b"
down_revision: str | None = "f5b0c8d2a1e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "product_attributes",
        # SQLAlchemy persists the names of the Python enum members, not their
        # lower-case values.  Existing attributes therefore need ``PRIMARY``.
        sa.Column(
            "source", sa.String(length=16), nullable=False, server_default="PRIMARY"
        ),
    )
    op.add_column(
        "product_attributes",
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )
    op.drop_constraint(
        "product_attribute_product_key_ukey",
        "product_attributes",
        type_="unique",
    )
    op.create_unique_constraint(
        "product_attribute_product_source_key_ukey",
        "product_attributes",
        ["product_id", "source", "key"],
    )
    op.alter_column("product_attributes", "source", server_default=None)
    op.alter_column("product_attributes", "position", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "product_attribute_product_source_key_ukey",
        "product_attributes",
        type_="unique",
    )
    op.create_unique_constraint(
        "product_attribute_product_key_ukey",
        "product_attributes",
        ["product_id", "key"],
    )
    op.drop_column("product_attributes", "position")
    op.drop_column("product_attributes", "source")
