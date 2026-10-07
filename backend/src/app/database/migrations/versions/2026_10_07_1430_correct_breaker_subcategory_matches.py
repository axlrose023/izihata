"""Move non-breaker accessories out of the power-breaker subcategory."""

# All predicate fragments below are literals defined in this migration.
# ruff: noqa: S608

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2d8f0c64a31"
down_revision: str | None = "7c41d08f3a62"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _category_id(connection: sa.Connection, slug: str):
    return connection.execute(
        sa.text("SELECT id FROM categories WHERE slug = :slug"), {"slug": slug}
    ).scalar_one_or_none()


def _subcategory_id(connection: sa.Connection, category_id, name: str):
    return connection.execute(
        sa.text(
            "SELECT id FROM subcategories "
            "WHERE category_id = :category_id AND name = :name"
        ),
        {"category_id": category_id, "name": name},
    ).scalar_one_or_none()


def _move(
    connection: sa.Connection,
    *,
    category_id,
    subcategory_id,
    where: str,
) -> None:
    connection.execute(
        sa.text(
            "UPDATE products SET category_id = :category_id, "
            "subcategory_id = :subcategory_id WHERE id IN ("
            "SELECT product_id FROM product_category_before_breaker_fix) AND ("
            + where
            + ")"
        ),
        {
            "category_id": category_id,
            "subcategory_id": subcategory_id,
        },
    )


def upgrade() -> None:
    op.create_table(
        "product_category_before_breaker_fix",
        sa.Column("product_id", sa.Uuid(), primary_key=True),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("subcategory_id", sa.Uuid(), nullable=True),
    )

    connection = op.get_bind()
    lowvoltage_id = _category_id(connection, "lowvoltage")
    if lowvoltage_id is None:
        return

    power_id = _subcategory_id(
        connection, lowvoltage_id, "Силові автоматичні вимикачі"
    )
    if power_id is None:
        return

    other_id = _category_id(connection, "other")
    if other_id is None:
        return

    # Leave only actual circuit breakers in this subcategory. The prior migration
    # matched any model code containing x/h + digits, which also caught accessories.
    connection.execute(
        sa.text(
            "INSERT INTO product_category_before_breaker_fix "
            "(product_id, category_id, subcategory_id) "
            "SELECT id, category_id, subcategory_id FROM products "
            "WHERE subcategory_id = :power_id AND NOT ("
            "name ILIKE '%силовий автоматичний вимикач%' OR "
            "name ILIKE '%автоматичний силовий вимикач%' OR "
            "name ILIKE '%силовий вимикач%' OR "
            "name ILIKE '%корпусний автоматичний вимикач%' OR "
            "name ILIKE '%MCCB%вимикач%' OR "
            "(name ILIKE '%автоматичний вимикач%' AND "
            "name ~* '(^|[^[:alnum:]])[xh][0-9]{2,4}([^[:alnum:]]|$)'))"
        ),
        {"power_id": power_id},
    )
    connection.execute(
        sa.text(
            "UPDATE products SET category_id = :other_id, subcategory_id = NULL "
            "WHERE subcategory_id = :power_id AND NOT ("
            "name ILIKE '%силовий автоматичний вимикач%' OR "
            "name ILIKE '%автоматичний силовий вимикач%' OR "
            "name ILIKE '%силовий вимикач%' OR "
            "name ILIKE '%корпусний автоматичний вимикач%' OR "
            "name ILIKE '%MCCB%вимикач%' OR "
            "(name ILIKE '%автоматичний вимикач%' AND "
            "name ~* '(^|[^[:alnum:]])[xh][0-9]{2,4}([^[:alnum:]]|$)'))"
        ),
        {"other_id": other_id, "power_id": power_id},
    )

    panels_id = _category_id(connection, "panels")
    panels_accessories_id = (
        _subcategory_id(connection, panels_id, "Аксесуари для електрощитів")
        if panels_id is not None
        else None
    )
    if panels_id is not None and panels_accessories_id is not None:
        _move(
            connection,
            category_id=panels_id,
            subcategory_id=panels_accessories_id,
            where=(
                "name ILIKE 'Лицьова панель%' OR "
                "name ILIKE 'Кришки вимірювальної касети%'"
            ),
        )

    accessories_id = _subcategory_id(
        connection,
        lowvoltage_id,
        "Додаткові пристрої до автоматичних вимикачів",
    )
    if accessories_id is not None:
        _move(
            connection,
            category_id=lowvoltage_id,
            subcategory_id=accessories_id,
            where=(
                "name ILIKE '%розчіплювач%' OR "
                "name ILIKE '%додатковий контакт%' OR "
                "name ILIKE '%сигнальний контакт%' OR "
                "name ILIKE '%дод.сигнальн.%контакт%' OR "
                "name ILIKE '%моторний привід%' OR "
                "name ILIKE '%поворотна ручка%' OR "
                "name ILIKE '%механічне блокування%' OR "
                "name ILIKE '%міжфазна перегородка%' OR "
                "name ILIKE '%межфазна перегородка%' OR "
                "name ILIKE '%заднє підключення%' OR "
                "name ILIKE '%полюс силовий до вимикача%'"
            ),
        )

    switching_id = _subcategory_id(
        connection, lowvoltage_id, "Рубильники та перемикачі"
    )
    if switching_id is not None:
        _move(
            connection,
            category_id=lowvoltage_id,
            subcategory_id=switching_id,
            where="name ILIKE '%роз''єднувач%'",
        )

    installation_id = _category_id(connection, "installation")
    terminals_id = (
        _subcategory_id(connection, installation_id, "Клемники")
        if installation_id is not None
        else None
    )
    if installation_id is not None and terminals_id is not None:
        _move(
            connection,
            category_id=installation_id,
            subcategory_id=terminals_id,
            where="name ILIKE '%тунельні клеми%'",
        )

    sockets_id = _category_id(connection, "sockets")
    sockets_subcategory_id = (
        _subcategory_id(
            connection, sockets_id, "Розетки (із заземленням, без заземлення)"
        )
        if sockets_id is not None
        else None
    )
    if sockets_id is not None and sockets_subcategory_id is not None:
        _move(
            connection,
            category_id=sockets_id,
            subcategory_id=sockets_subcategory_id,
            where="name ILIKE '%силова розетка%'",
        )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE products AS product SET "
            "category_id = prior.category_id, "
            "subcategory_id = prior.subcategory_id "
            "FROM product_category_before_breaker_fix AS prior "
            "WHERE product.id = prior.product_id"
        )
    )
    op.drop_table("product_category_before_breaker_fix")
