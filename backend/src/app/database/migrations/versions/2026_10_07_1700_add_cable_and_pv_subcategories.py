"""Add electrical installation subcategories and recategorize matching products."""

# All predicate fragments below are fixed product-name filters.
# ruff: noqa: S608

from collections.abc import Sequence
from typing import cast
from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "d8a1f43b2c70"
down_revision: str | None = "f0e21d5c9a74"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _category(connection: sa.Connection, slug: str) -> UUID | None:
    return connection.execute(
        sa.text("SELECT id FROM categories WHERE slug = :slug"), {"slug": slug}
    ).scalar_one_or_none()


def _subcategory(
    connection: sa.Connection, category_id: UUID, name: str
) -> UUID | None:
    return connection.execute(
        sa.text(
            "SELECT id FROM subcategories "
            "WHERE category_id = :category_id AND name = :name"
        ),
        {"category_id": category_id, "name": name},
    ).scalar_one_or_none()


def _ensure_subcategory(
    connection: sa.Connection,
    *,
    category_id: UUID,
    category_slug: str,
    name: str,
) -> UUID:
    existing_id = _subcategory(connection, category_id, name)
    if existing_id is not None:
        return existing_id

    position = connection.execute(
        sa.text(
            "SELECT COALESCE(MAX(position), -1) + 1 FROM subcategories "
            "WHERE category_id = :category_id"
        ),
        {"category_id": category_id},
    ).scalar_one()
    slug_position = position + 1
    while connection.execute(
        sa.text(
            "SELECT 1 FROM subcategories "
            "WHERE category_id = :category_id AND slug = :slug"
        ),
        {"category_id": category_id, "slug": f"{category_slug}-{slug_position}"},
    ).scalar_one_or_none():
        slug_position += 1

    subcategory_id = cast(
        UUID,
        connection.execute(
            sa.text(
                "INSERT INTO subcategories "
                "(id, category_id, slug, name, position, is_active) "
                "VALUES (:id, :category_id, :slug, :name, :position, true) "
                "RETURNING id"
            ),
            {
                "id": uuid4(),
                "category_id": category_id,
                "slug": f"{category_slug}-{slug_position}",
                "name": name,
                "position": position,
            },
        ).scalar_one(),
    )
    connection.execute(
        sa.text(
            "INSERT INTO subcategories_created_by_electrical_taxonomy (id) VALUES (:id)"
        ),
        {"id": subcategory_id},
    )
    return subcategory_id


def _move_products(
    connection: sa.Connection,
    *,
    category_id: UUID,
    subcategory_id: UUID,
    where: str,
) -> None:
    changed = (
        f"({where}) AND (category_id IS DISTINCT FROM :target_category_id "
        "OR subcategory_id IS DISTINCT FROM :target_subcategory_id)"
    )
    values = {
        "target_category_id": category_id,
        "target_subcategory_id": subcategory_id,
    }
    connection.execute(
        sa.text(
            "INSERT INTO product_categories_before_electrical_taxonomy "
            "(product_id, category_id, subcategory_id) "
            "SELECT id, category_id, subcategory_id FROM products WHERE "
            + changed
            + " ON CONFLICT (product_id) DO NOTHING"
        ),
        values,
    )
    connection.execute(
        sa.text(
            "UPDATE products SET category_id = :target_category_id, "
            "subcategory_id = :target_subcategory_id WHERE " + changed
        ),
        values,
    )


def upgrade() -> None:
    op.create_table(
        "product_categories_before_electrical_taxonomy",
        sa.Column("product_id", sa.Uuid(), primary_key=True),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("subcategory_id", sa.Uuid(), nullable=True),
    )
    op.create_table(
        "subcategories_created_by_electrical_taxonomy",
        sa.Column("id", sa.Uuid(), primary_key=True),
    )

    connection = op.get_bind()
    destinations = (
        (
            "power",
            "Щити захисту PV систем",
            "name ILIKE '%щит%PV%' OR name ILIKE '%PV%щит%' "
            "OR name ILIKE '%щит%фотоелектр%' OR name ILIKE '%фотоелектр%щит%' "
            "OR name ILIKE '%щит%сонячн%' OR name ILIKE '%сонячн%щит%'",
        ),
        (
            "cabletrays",
            "Хомути (стяжки кабельні)",
            "name ILIKE '%хомут кабельн%' OR name ILIKE '%хомути кабельн%' "
            "OR name ILIKE '%хомут нейлон%' OR name ILIKE '%хомути нейлон%' "
            "OR name ILIKE '%кабельна стяжк%' OR name ILIKE '%стяжка кабельн%' "
            "OR name ILIKE '%кабельні стяжк%' OR name ILIKE '%стяжки кабельн%'",
        ),
        (
            "cabletrays",
            "Кабельні тримачі",
            "name ILIKE '%тримач%для кабел%' "
            "OR name ILIKE '%утримувач провод%' "
            "OR name ILIKE '%адаптер для утримувача провод%'",
        ),
        (
            "installation",
            "Термоусаджувальна трубка",
            "name ILIKE '%термоусаджувальн%трубк%' "
            "OR name ILIKE '%термоусадочн%трубк%' "
            "OR name ILIKE '%трубк%термоусаджувальн%' "
            "OR name ILIKE '%трубк%термоусадочн%'",
        ),
        (
            "installation",
            "Ізолента",
            "name ILIKE '%ізолент%' OR name ILIKE '%изолент%' "
            "OR name ILIKE '%ізострічк%' OR name ILIKE '%ізоляційна стрічк%' "
            "OR name ILIKE '%стрічка ізоляційна%'",
        ),
    )

    for category_slug, subcategory_name, where in destinations:
        category_id = _category(connection, category_slug)
        if category_id is None:
            continue
        subcategory_id = _ensure_subcategory(
            connection,
            category_id=category_id,
            category_slug=category_slug,
            name=subcategory_name,
        )
        _move_products(
            connection,
            category_id=category_id,
            subcategory_id=subcategory_id,
            where=where,
        )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE products AS product SET "
            "category_id = prior.category_id, "
            "subcategory_id = prior.subcategory_id "
            "FROM product_categories_before_electrical_taxonomy AS prior "
            "WHERE product.id = prior.product_id"
        )
    )
    connection.execute(
        sa.text(
            "DELETE FROM subcategories WHERE id IN ("
            "SELECT id FROM subcategories_created_by_electrical_taxonomy) "
            "AND NOT EXISTS (SELECT 1 FROM products "
            "WHERE products.subcategory_id = subcategories.id)"
        )
    )
    op.drop_table("subcategories_created_by_electrical_taxonomy")
    op.drop_table("product_categories_before_electrical_taxonomy")
