"""add product reviews

Revision ID: 9c15fdac51fe
Revises: 62f5d841c0a7
Create Date: 2026-08-11 17:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9c15fdac51fe"
down_revision: str | None = "62f5d841c0a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_reviews",
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("author", sa.String(length=120), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column("is_featured", sa.Boolean(), nullable=False),
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
            "rating >= 1 AND rating <= 5",
            name=op.f("product_reviews_review_rating_range_check"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("product_reviews_product_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("product_reviews_pkey")),
    )
    op.create_index(
        op.f("product_reviews_is_featured_idx"),
        "product_reviews",
        ["is_featured"],
    )
    op.create_index(
        op.f("product_reviews_is_published_idx"),
        "product_reviews",
        ["is_published"],
    )
    op.create_index(
        op.f("product_reviews_product_id_idx"),
        "product_reviews",
        ["product_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("product_reviews_product_id_idx"),
        table_name="product_reviews",
    )
    op.drop_index(
        op.f("product_reviews_is_featured_idx"),
        table_name="product_reviews",
    )
    op.drop_index(
        op.f("product_reviews_is_published_idx"),
        table_name="product_reviews",
    )
    op.drop_table("product_reviews")
