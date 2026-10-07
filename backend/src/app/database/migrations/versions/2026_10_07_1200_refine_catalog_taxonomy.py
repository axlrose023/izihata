"""Split circuit breaker families and place related catalog products."""

# All predicate fragments below are literals defined in this migration.
# ruff: noqa: S608

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "7c41d08f3a62"
down_revision: str | None = "0a52f370c164"
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


def _rename_subcategory(
    connection: sa.Connection,
    category_id,
    old_name: str,
    new_name: str,
) -> None:
    old_id = _subcategory_id(connection, category_id, old_name)
    if old_id is not None and _subcategory_id(connection, category_id, new_name) is None:
        connection.execute(
            sa.text("UPDATE subcategories SET name = :new_name WHERE id = :id"),
            {"id": old_id, "new_name": new_name},
        )


def _ensure_subcategory(
    connection: sa.Connection,
    category_id,
    *,
    slug: str,
    name: str,
    position: int,
):
    existing = _subcategory_id(connection, category_id, name)
    if existing is not None:
        return existing
    subcategory_id = uuid4()
    connection.execute(
        sa.text(
            "INSERT INTO subcategories "
            "(id, category_id, slug, name, position, is_active) "
            "VALUES (:id, :category_id, :slug, :name, :position, true)"
        ),
        {
            "id": subcategory_id,
            "category_id": category_id,
            "slug": slug,
            "name": name,
            "position": position,
        },
    )
    return subcategory_id


def _move_named_products(
    connection: sa.Connection,
    *,
    category_id,
    subcategory_id,
    where: str,
    params: dict[str, object],
) -> None:
    query = (
        "UPDATE products SET category_id = :category_id, "
        "subcategory_id = :subcategory_id WHERE "
        + where
    )
    connection.execute(
        sa.text(query),
        {**params, "category_id": category_id, "subcategory_id": subcategory_id},
    )


def upgrade() -> None:
    connection = op.get_bind()
    categories = {
        slug: _category_id(connection, slug)
        for slug in ("lowvoltage", "panels", "light", "power", "other", "installation")
    }
    if any(categories[slug] is None for slug in ("lowvoltage", "panels", "light")):
        # An unseeded installation gets the current taxonomy from catalog.json.
        return

    lowvoltage_id = categories["lowvoltage"]
    panels_id = categories["panels"]
    light_id = categories["light"]

    _rename_subcategory(
        connection,
        lowvoltage_id,
        "Автоматичні вимикачі (модульні / корпусні / повітряні)",
        "Модульні автоматичні вимикачі",
    )
    _rename_subcategory(
        connection,
        lowvoltage_id,
        "Додаткові пристрої до автоматів",
        "Додаткові пристрої до автоматичних вимикачів",
    )
    _rename_subcategory(
        connection,
        lowvoltage_id,
        "Диференціальні автомати",
        "Диференціальні автоматичні вимикачі",
    )
    _rename_subcategory(
        connection,
        lowvoltage_id,
        "Автомати захисту двигуна",
        "Автоматичні вимикачі захисту двигуна",
    )

    modular_id = _subcategory_id(
        connection, lowvoltage_id, "Модульні автоматичні вимикачі"
    )
    if modular_id is None:
        return

    lowvoltage_air_id = _ensure_subcategory(
        connection,
        lowvoltage_id,
        slug="lowvoltage-16",
        name="Повітряні автоматичні вимикачі",
        position=15,
    )
    lowvoltage_power_id = _ensure_subcategory(
        connection,
        lowvoltage_id,
        slug="lowvoltage-15",
        name="Силові автоматичні вимикачі",
        position=14,
    )
    lowvoltage_motor_id = _ensure_subcategory(
        connection,
        lowvoltage_id,
        slug="lowvoltage-6",
        name="Автоматичні вимикачі захисту двигуна",
        position=5,
    )
    lowvoltage_accessories_id = _subcategory_id(
        connection,
        lowvoltage_id,
        "Додаткові пристрої до автоматичних вимикачів",
    )
    lowvoltage_differential_id = _subcategory_id(
        connection,
        lowvoltage_id,
        "Диференціальні автоматичні вимикачі",
    )
    panel_avr_id = _ensure_subcategory(
        connection,
        panels_id,
        slug="panels-14",
        name="\u0410\u0412\u0420 (автоматичний ввід резерву)",
        position=13,
    )
    panel_yatp_id = _ensure_subcategory(
        connection,
        panels_id,
        slug="panels-15",
        name="ЯТП (ящик із знижувальним трансформатором)",
        position=14,
    )
    light_power_id = _ensure_subcategory(
        connection,
        light_id,
        slug="light-9",
        name="Блоки живлення",
        position=8,
    )

    _move_named_products(
        connection,
        category_id=lowvoltage_id,
        subcategory_id=lowvoltage_motor_id,
        where=(
            "category_id IN (:lowvoltage_id, :other_id) AND "
            "name ILIKE '%вимикач%' AND name ILIKE '%захисту двиг%'"
        ),
        params={"lowvoltage_id": lowvoltage_id, "other_id": categories["other"]},
    )
    if lowvoltage_accessories_id is not None:
        _move_named_products(
            connection,
            category_id=lowvoltage_id,
            subcategory_id=lowvoltage_accessories_id,
            where=(
                "category_id = :lowvoltage_id AND "
                "name ILIKE '%розчіплювач%для автоматів захисту двиг%'"
            ),
            params={"lowvoltage_id": lowvoltage_id},
        )
    if lowvoltage_differential_id is not None:
        _move_named_products(
            connection,
            category_id=lowvoltage_id,
            subcategory_id=lowvoltage_differential_id,
            where=(
                "category_id = :lowvoltage_id AND name ILIKE '%дифавтомат%'"
            ),
            params={"lowvoltage_id": lowvoltage_id},
        )
    _move_named_products(
        connection,
        category_id=lowvoltage_id,
        subcategory_id=lowvoltage_air_id,
        where=(
            "category_id IN (:lowvoltage_id, :other_id) AND "
            "name ILIKE '%повітр%' AND name ILIKE '%вим%'"
        ),
        params={"lowvoltage_id": lowvoltage_id, "other_id": categories["other"]},
    )
    _move_named_products(
        connection,
        category_id=lowvoltage_id,
        subcategory_id=lowvoltage_power_id,
        where=(
            "category_id IN (:lowvoltage_id, :other_id) AND "
            "(name ILIKE '%силовий автоматичний вимикач%' OR "
            "name ILIKE '%автоматичний силовий вимикач%' OR "
            "name ILIKE '%силовий вимикач%' OR "
            "name ILIKE '%корпусний автоматичний вимикач%' OR "
            "name ILIKE '%MCCB%вимикач%' OR "
            "(name ILIKE '%автоматичний вимикач%' AND "
            "name ~* '(^|[^[:alnum:]])[xh][0-9]{2,4}([^[:alnum:]]|$)'))"
        ),
        params={"lowvoltage_id": lowvoltage_id, "other_id": categories["other"]},
    )
    if categories["other"] is not None:
        _move_named_products(
            connection,
            category_id=lowvoltage_id,
            subcategory_id=modular_id,
            where=(
                "category_id = :other_id AND "
                "name ILIKE '%автоматичний вимикач%' AND "
                "name NOT ILIKE '%силов%' AND name NOT ILIKE '%повітр%' AND "
                "name NOT ILIKE '%захисту двиг%' AND "
                "name NOT ILIKE '%дифавтомат%' AND "
                "name NOT ILIKE '%диференц%' AND "
                "name !~* '(^|[^[:alnum:]])[xh][0-9]{2,4}([^[:alnum:]]|$)'"
            ),
            params={"other_id": categories["other"]},
        )
    _move_named_products(
        connection,
        category_id=panels_id,
        subcategory_id=panel_avr_id,
        where="name ILIKE '%авр%'",
        params={},
    )
    _move_named_products(
        connection,
        category_id=panels_id,
        subcategory_id=panel_yatp_id,
        where="name ILIKE '%ятп%'",
        params={},
    )
    _move_named_products(
        connection,
        category_id=light_id,
        subcategory_id=light_power_id,
        where="name ILIKE '%блок живлення%'",
        params={},
    )
    if categories["installation"] is not None:
        connection.execute(
            sa.text(
                "UPDATE products SET category_id = :category_id, "
                "subcategory_id = :subcategory_id WHERE sku = 'AX-10045'"
            ),
            {"category_id": light_id, "subcategory_id": light_power_id},
        )


def downgrade() -> None:
    connection = op.get_bind()
    categories = {
        slug: _category_id(connection, slug)
        for slug in ("lowvoltage", "panels", "light", "installation", "other")
    }
    lowvoltage_id = categories["lowvoltage"]
    if lowvoltage_id is None:
        return
    modular_id = _subcategory_id(
        connection, lowvoltage_id, "Модульні автоматичні вимикачі"
    )
    for name in (
        "Силові автоматичні вимикачі",
        "Повітряні автоматичні вимикачі",
    ):
        subcategory_id = _subcategory_id(connection, lowvoltage_id, name)
        if subcategory_id is not None and modular_id is not None:
            connection.execute(
                sa.text(
                    "UPDATE products SET subcategory_id = :target_id "
                    "WHERE subcategory_id = :source_id"
                ),
                {"target_id": modular_id, "source_id": subcategory_id},
            )

    for name in (
        "\u0410\u0412\u0420 (автоматичний ввід резерву)",
        "ЯТП (ящик із знижувальним трансформатором)",
    ):
        if categories["panels"] is None:
            break
        subcategory_id = _subcategory_id(connection, categories["panels"], name)
        if subcategory_id is not None and categories["other"] is not None:
            connection.execute(
                sa.text(
                    "UPDATE products SET category_id = :category_id, "
                    "subcategory_id = NULL WHERE subcategory_id = :subcategory_id"
                ),
                {
                    "category_id": categories["other"],
                    "subcategory_id": subcategory_id,
                },
            )
    if categories["light"] is not None:
        power_id = _subcategory_id(connection, categories["light"], "Блоки живлення")
        if power_id is not None and categories["installation"] is not None:
            connection.execute(
                sa.text(
                    "UPDATE products SET category_id = :category_id, "
                    "subcategory_id = NULL WHERE subcategory_id = :subcategory_id"
                ),
                {
                    "category_id": categories["installation"],
                    "subcategory_id": power_id,
                },
            )

    connection.execute(
        sa.text(
            "UPDATE subcategories SET name = 'Автоматичні вимикачі "
            "(модульні / корпусні / повітряні)' "
            "WHERE category_id = :category_id AND name = 'Модульні автоматичні вимикачі'"
        ),
        {"category_id": lowvoltage_id},
    )
    connection.execute(
        sa.text(
            "UPDATE subcategories SET name = 'Додаткові пристрої до автоматів' "
            "WHERE category_id = :category_id AND "
            "name = 'Додаткові пристрої до автоматичних вимикачів'"
        ),
        {"category_id": lowvoltage_id},
    )
    connection.execute(
        sa.text(
            "UPDATE subcategories SET name = 'Диференціальні автомати' "
            "WHERE category_id = :category_id AND "
            "name = 'Диференціальні автоматичні вимикачі'"
        ),
        {"category_id": lowvoltage_id},
    )
    connection.execute(
        sa.text(
            "UPDATE subcategories SET name = 'Автомати захисту двигуна' "
            "WHERE category_id = :category_id AND "
            "name = 'Автоматичні вимикачі захисту двигуна'"
        ),
        {"category_id": lowvoltage_id},
    )
    for category_id, names in (
        (
            lowvoltage_id,
            (
                "Силові автоматичні вимикачі",
                "Повітряні автоматичні вимикачі",
            ),
        ),
        (
            categories["panels"],
            (
                "\u0410\u0412\u0420 (автоматичний ввід резерву)",
                "ЯТП (ящик із знижувальним трансформатором)",
            ),
        ),
        (categories["light"], ("Блоки живлення",)),
    ):
        if category_id is None:
            continue
        for name in names:
            connection.execute(
                sa.text(
                    "DELETE FROM subcategories "
                    "WHERE category_id = :category_id AND name = :name"
                ),
                {"category_id": category_id, "name": name},
            )
