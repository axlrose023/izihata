"""Store generated image sizes without replacing supplier originals."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "96b47f52d109"
down_revision: str | None = "2f41d980ca73"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("products", sa.Column("image_variants", sa.JSON(), nullable=True))
    op.add_column(
        "product_media", sa.Column("image_variants", sa.JSON(), nullable=True)
    )
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_products_image_url",
            "products",
            ["image_url"],
            postgresql_concurrently=True,
        )
        op.create_index(
            "ix_product_media_url",
            "product_media",
            ["url"],
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    op.drop_index("ix_products_image_url", table_name="products")
    op.drop_index("ix_product_media_url", table_name="product_media")
    op.drop_column("product_media", "image_variants")
    op.drop_column("products", "image_variants")
