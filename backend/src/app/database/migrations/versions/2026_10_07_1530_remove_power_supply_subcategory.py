"""Remove the old power-category entry after moving supplies to lighting."""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from alembic import op

revision: str = "f0e21d5c9a74"
down_revision: str | None = "b2d8f0c64a31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _category_id(connection: sa.Connection, slug: str) -> UUID | None:
    return connection.execute(
        sa.text("SELECT id FROM categories WHERE slug = :slug"), {"slug": slug}
    ).scalar_one_or_none()


def _subcategory_id(
    connection: sa.Connection, category_id: UUID | None, name: str
) -> UUID | None:
    return connection.execute(
        sa.text(
            "SELECT id FROM subcategories "
            "WHERE category_id = :category_id AND name = :name"
        ),
        {"category_id": category_id, "name": name},
    ).scalar_one_or_none()


def upgrade() -> None:
    op.create_table(
        "power_supply_subcategory_before_move",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "product_categories_before_power_supply_move",
        sa.Column("product_id", sa.Uuid(), primary_key=True),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("subcategory_id", sa.Uuid(), nullable=True),
    )

    connection = op.get_bind()
    power_id = _category_id(connection, "power")
    light_id = _category_id(connection, "light")
    if power_id is None or light_id is None:
        return

    old_subcategory_id = _subcategory_id(connection, power_id, "Блоки живлення")
    light_subcategory_id = _subcategory_id(connection, light_id, "Блоки живлення")
    if old_subcategory_id is None or light_subcategory_id is None:
        return

    connection.execute(
        sa.text(
            "INSERT INTO power_supply_subcategory_before_move "
            "(id, category_id, slug, name, position, is_active) "
            "SELECT id, category_id, slug, name, position, is_active "
            "FROM subcategories WHERE id = :subcategory_id"
        ),
        {"subcategory_id": old_subcategory_id},
    )
    connection.execute(
        sa.text(
            "INSERT INTO product_categories_before_power_supply_move "
            "(product_id, category_id, subcategory_id) "
            "SELECT id, category_id, subcategory_id FROM products "
            "WHERE subcategory_id = :subcategory_id"
        ),
        {"subcategory_id": old_subcategory_id},
    )
    connection.execute(
        sa.text(
            "UPDATE products SET category_id = :light_id, "
            "subcategory_id = :light_subcategory_id "
            "WHERE subcategory_id = :old_subcategory_id"
        ),
        {
            "light_id": light_id,
            "light_subcategory_id": light_subcategory_id,
            "old_subcategory_id": old_subcategory_id,
        },
    )
    connection.execute(
        sa.text(
            "DELETE FROM subcategories WHERE id = :subcategory_id AND NOT EXISTS ("
            "SELECT 1 FROM products WHERE subcategory_id = :subcategory_id)"
        ),
        {"subcategory_id": old_subcategory_id},
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "INSERT INTO subcategories (id, category_id, slug, name, position, is_active) "
            "SELECT prior.id, prior.category_id, prior.slug, prior.name, "
            "prior.position, prior.is_active "
            "FROM power_supply_subcategory_before_move AS prior "
            "WHERE NOT EXISTS (SELECT 1 FROM subcategories WHERE id = prior.id)"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE products AS product SET "
            "category_id = prior.category_id, "
            "subcategory_id = prior.subcategory_id "
            "FROM product_categories_before_power_supply_move AS prior "
            "WHERE product.id = prior.product_id"
        )
    )
    op.drop_table("product_categories_before_power_supply_move")
    op.drop_table("power_supply_subcategory_before_move")
