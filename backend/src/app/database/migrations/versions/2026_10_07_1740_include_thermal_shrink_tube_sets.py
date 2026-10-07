"""Move thermal shrink tube sets into their dedicated subcategory."""

# The product-name predicate below is fixed migration data.
# ruff: noqa: S608

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e3b7a6d91c42"
down_revision: str | None = "d8a1f43b2c70"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_categories_before_shrink_tube_sets",
        sa.Column("product_id", sa.Uuid(), primary_key=True),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("subcategory_id", sa.Uuid(), nullable=True),
    )

    connection = op.get_bind()
    destination = connection.execute(
        sa.text(
            "SELECT category.id, subcategory.id "
            "FROM categories AS category "
            "JOIN subcategories AS subcategory "
            "ON subcategory.category_id = category.id "
            "WHERE category.slug = :category_slug "
            "AND subcategory.name = :subcategory_name"
        ),
        {
            "category_slug": "installation",
            "subcategory_name": "Термоусаджувальна трубка",
        },
    ).one_or_none()
    if destination is None:
        return

    category_id, subcategory_id = destination
    where = (
        "(name ILIKE '%термоусаджувальн%труб%' "
        "OR name ILIKE '%термоусадочн%труб%' "
        "OR name ILIKE '%труб%термоусаджувальн%' "
        "OR name ILIKE '%труб%термоусадочн%') "
        "AND (category_id IS DISTINCT FROM :category_id "
        "OR subcategory_id IS DISTINCT FROM :subcategory_id)"
    )
    values = {"category_id": category_id, "subcategory_id": subcategory_id}
    connection.execute(
        sa.text(
            "INSERT INTO product_categories_before_shrink_tube_sets "
            "(product_id, category_id, subcategory_id) "
            "SELECT id, category_id, subcategory_id FROM products WHERE "
            + where
        ),
        values,
    )
    connection.execute(
        sa.text(
            "UPDATE products SET category_id = :category_id, "
            "subcategory_id = :subcategory_id WHERE "
            + where
        ),
        values,
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE products AS product SET "
            "category_id = prior.category_id, "
            "subcategory_id = prior.subcategory_id "
            "FROM product_categories_before_shrink_tube_sets AS prior "
            "WHERE product.id = prior.product_id"
        )
    )
    op.drop_table("product_categories_before_shrink_tube_sets")
