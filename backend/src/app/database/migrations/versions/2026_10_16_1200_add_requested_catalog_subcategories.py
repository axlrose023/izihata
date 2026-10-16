"""Add the requested subcategories and classify matching catalog products."""

# The product-name filters below are fixed migration data.
# ruff: noqa: S608

from collections.abc import Sequence
from typing import cast
from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "ef20261016a120"
down_revision: str | None = "c58af6b2d091"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _category_id(connection: sa.Connection, slug: str) -> UUID | None:
    return connection.execute(
        sa.text("SELECT id FROM categories WHERE slug = :slug"), {"slug": slug}
    ).scalar_one_or_none()


def _subcategory_id(
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
    existing_id = _subcategory_id(connection, category_id, name)
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
            "INSERT INTO requested_subcategories_created (id) VALUES (:id)"
        ),
        {"id": subcategory_id},
    )
    return subcategory_id


def _rename_or_merge_intermediate_relays(connection: sa.Connection) -> None:
    category_id = _category_id(connection, "relay")
    if category_id is None:
        return

    old_name = "Допоміжні реле"
    new_name = "Проміжні реле"
    old_id = _subcategory_id(connection, category_id, old_name)
    if old_id is None:
        return

    connection.execute(
        sa.text(
            "INSERT INTO requested_subcategory_rows "
            "(id, category_id, slug, name, position, is_active, created_at, updated_at, action) "
            "SELECT id, category_id, slug, name, position, is_active, created_at, updated_at, 'rename' "
            "FROM subcategories WHERE id = :id"
        ),
        {"id": old_id},
    )
    new_id = _subcategory_id(connection, category_id, new_name)
    if new_id is None:
        connection.execute(
            sa.text("UPDATE subcategories SET name = :name WHERE id = :id"),
            {"name": new_name, "id": old_id},
        )
        return

    _move_products(
        connection,
        category_id=category_id,
        subcategory_id=new_id,
        where="subcategory_id = :old_subcategory_id",
        params={"old_subcategory_id": old_id},
    )
    connection.execute(
        sa.text(
            "UPDATE requested_subcategory_rows SET action = 'merge' WHERE id = :id"
        ),
        {"id": old_id},
    )
    connection.execute(
        sa.text("DELETE FROM subcategories WHERE id = :id"), {"id": old_id}
    )


def _move_products(
    connection: sa.Connection,
    *,
    category_id: UUID,
    subcategory_id: UUID,
    where: str,
    params: dict[str, object] | None = None,
) -> None:
    changed = (
        f"({where}) AND (category_id IS DISTINCT FROM :target_category_id "
        "OR subcategory_id IS DISTINCT FROM :target_subcategory_id)"
    )
    values = {
        **(params or {}),
        "target_category_id": category_id,
        "target_subcategory_id": subcategory_id,
    }
    connection.execute(
        sa.text(
            "INSERT INTO requested_product_categories_before "
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
            "subcategory_id = :target_subcategory_id WHERE "
            + changed
        ),
        values,
    )


def upgrade() -> None:
    op.create_table(
        "requested_product_categories_before",
        sa.Column("product_id", sa.Uuid(), primary_key=True),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("subcategory_id", sa.Uuid(), nullable=True),
    )
    op.create_table(
        "requested_subcategories_created",
        sa.Column("id", sa.Uuid(), primary_key=True),
    )
    op.create_table(
        "requested_subcategory_rows",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(96), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
    )

    connection = op.get_bind()
    _rename_or_merge_intermediate_relays(connection)

    requested = (
        ("lowvoltage", "Котушки управління до контакторів"),
        ("lowvoltage", "Додаткове обладнання для контакторів"),
        ("lowvoltage", "Теплові реле"),
        ("relay", "Реле захисту двигуна"),
        ("relay", "Імпульсні реле"),
        ("relay", "Розеточні реле"),
        ("installation", "Блоки розподільчі"),
        ("installation", "Ізолятори"),
        ("installation", "Маркери кабельні"),
        ("installation", "Шайби мідно-алюмінієві"),
        ("installation", "Вироби для кріплення"),
        ("cabletrays", "Арматура СІП"),
        ("cabletrays", "Аксесуари для труб ПВХ"),
        ("cabletrays", "Колодязі кабельні"),
    )
    subcategories: dict[tuple[str, str], tuple[UUID, UUID]] = {}
    for category_slug, name in requested:
        category_id = _category_id(connection, category_slug)
        if category_id is None:
            continue
        subcategory_id = _ensure_subcategory(
            connection,
            category_id=category_id,
            category_slug=category_slug,
            name=name,
        )
        subcategories[(category_slug, name)] = (category_id, subcategory_id)

    product_filters = (
        (
            "lowvoltage",
            "Котушки управління до контакторів",
            "name ILIKE '%котушк%контактор%'",
        ),
        (
            "lowvoltage",
            "Додаткове обладнання для контакторів",
            "name ILIKE 'Блок реверса контактора%' "
            "OR name ILIKE 'Додаткове обладнання%контактор%' "
            "OR name ILIKE 'Адаптер теплового реле%' "
            "OR name ILIKE '%основа теплового реле%'",
        ),
        (
            "lowvoltage",
            "Теплові реле",
            "name ILIKE 'Теплове реле%' "
            "OR name ILIKE 'Реле теплове до контакторів%'",
        ),
        (
            "relay",
            "Реле захисту двигуна",
            "name ILIKE 'Реле%захисту двигуна%'",
        ),
        (
            "relay",
            "Імпульсні реле",
            "name ILIKE 'Імпульсне реле%' OR name ILIKE 'Реле імпульсне%'",
        ),
        (
            "relay",
            "Розеточні реле",
            "name ILIKE 'Реле%розеткове%' OR name ILIKE 'Реле%розеточне%'",
        ),
        (
            "installation",
            "Блоки розподільчі",
            "name ILIKE 'Блок розподільчий%' "
            "OR name ILIKE 'Розподільчий блок%' "
            "OR name ILIKE 'Блок розподільний%'",
        ),
        (
            "installation",
            "Ізолятори",
            "name ILIKE 'Ізолятор%'",
        ),
        (
            "installation",
            "Маркери кабельні",
            "name ILIKE 'Комплект кабельного маркування%' "
            "OR name ILIKE 'Маркування EC-%'",
        ),
        (
            "installation",
            "Шайби мідно-алюмінієві",
            "name ILIKE '%шайб%' AND (name ILIKE '%мідно-алюмінієв%' "
            "OR name ILIKE '%алюмінієв%мідн%' OR name ILIKE '%мідн%алюмін%')",
        ),
        (
            "installation",
            "Вироби для кріплення",
            "name ILIKE 'Виріб для кріплення%' "
            "OR name ILIKE 'Вироби для кріплення%' "
            "OR name ILIKE 'Кріпильні вироби%'",
        ),
        (
            "cabletrays",
            "Арматура СІП",
            "(name ILIKE '%проколюючий затискач%' "
            "OR name ILIKE '%арматура СІП%') "
            "AND name NOT ILIKE '%для обмежувачів перенапруги%'",
        ),
        (
            "cabletrays",
            "Аксесуари для труб ПВХ",
            "(name ILIKE '%ПВХ%' OR name ILIKE '%PVC%') "
            "AND (name ILIKE '%муфт%' OR name ILIKE '%колін%' "
            "OR name ILIKE '%трійник%' "
            "OR name ILIKE '%з''єднувач%' OR name ILIKE '%перехідник%')",
        ),
        (
            "cabletrays",
            "Колодязі кабельні",
            "name ILIKE '%колодяз%кабель%' "
            "OR name ILIKE '%кабельн%колодяз%'",
        ),
    )
    for category_slug, name, where in product_filters:
        destination = subcategories.get((category_slug, name))
        if destination is None:
            continue
        category_id, subcategory_id = destination
        _move_products(
            connection,
            category_id=category_id,
            subcategory_id=subcategory_id,
            where=where,
        )

    lowvoltage = _category_id(connection, "lowvoltage")
    relay_contactor_id = (
        _subcategory_id(connection, lowvoltage, "Контактори")
        if lowvoltage is not None
        else None
    )
    if lowvoltage is not None and relay_contactor_id is not None:
        _move_products(
            connection,
            category_id=lowvoltage,
            subcategory_id=relay_contactor_id,
            where="name ILIKE 'Модульний контактор%'",
        )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "INSERT INTO subcategories "
            "(id, category_id, slug, name, position, is_active, created_at, updated_at) "
            "SELECT id, category_id, slug, name, position, is_active, created_at, updated_at "
            "FROM requested_subcategory_rows WHERE action = 'merge' "
            "ON CONFLICT (id) DO NOTHING"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE products AS product SET "
            "category_id = prior.category_id, "
            "subcategory_id = prior.subcategory_id "
            "FROM requested_product_categories_before AS prior "
            "WHERE product.id = prior.product_id"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE subcategories SET name = prior.name "
            "FROM requested_subcategory_rows AS prior "
            "WHERE subcategories.id = prior.id AND prior.action = 'rename'"
        )
    )
    connection.execute(
        sa.text(
            "DELETE FROM subcategories WHERE id IN ("
            "SELECT id FROM requested_subcategories_created) "
            "AND NOT EXISTS (SELECT 1 FROM products "
            "WHERE products.subcategory_id = subcategories.id)"
        )
    )
    op.drop_table("requested_subcategory_rows")
    op.drop_table("requested_subcategories_created")
    op.drop_table("requested_product_categories_before")
