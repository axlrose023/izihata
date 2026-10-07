"""Correct reviewed accessory assignments and place AVR under low voltage.

The SKU lists were reviewed against the 2026-10-07 supplier catalog. Freeze the
selection here so future changes to import rules cannot change this migration.
Only category references are modified; supplier content is preserved.
"""

# Selection fragments are fixed literals and reviewed SKUs are bound parameters.
# ruff: noqa: S608
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a07d6c219e54"
down_revision: str | None = "e3b7a6d91c42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REVIEWED_MOVES = (
    (
        "cabletrays",
        "Кабельні тримачі",
        (
            "1066",
            "1067",
            "1069",
            "1070",
            "1101",
            "2062",
            "2064",
            "2066",
            "2068",
            "2070",
            "2072",
            "2074",
            "2076",
            "2078",
            "6939",
            "6940",
            "872",
            "881",
            "889",
            "A0150090025",
            "A0150090053",
            "A0150090054",
            "A0150090055",
            "A0150090078",
            "A0150090104",
            "A0150090105",
            "A0150090106",
            "A0150090176",
            "ACKO-1102",
            "m0080002",
            "p046002",
            "p046003",
            "s015097",
            "s015098",
            "s015099",
            "s015100",
        ),
    ),
    (
        "lowvoltage",
        "Додаткові пристрої до автоматичних вимикачів",
        (
            "1908411",
            "1908412",
            "2069004",
            "2159301",
            "2159311",
            "2159312",
            "2159320",
            "2159321",
            "30017",
            "30018",
            "4600170",
            "4600180",
            "4646632",
            "4646633",
            "4646634",
            "4648027",
            "4648028",
            "4648030",
            "4671135",
            "4671136",
            "4671137",
            "4671147",
            "4671148",
            "4671149",
            "4671152",
            "4671153",
            "4671154",
            "4671157",
            "4671953",
            "4671954",
            "4671955",
            "4671956",
            "4671957",
            "4671958",
            "4672299",
            "4672300",
            "4672301",
            "4672305",
            "4672306",
            "4672341",
            "4672342",
            "4672390",
            "4672391",
            "4673213",
            "4673214",
            "4673215",
            "4673216",
            "4673217",
            "4673218",
            "4673219",
            "4673220",
            "4673221",
            "4673222",
            "4673223",
            "4673224",
            "4697016",
            "4697017",
            "4697034",
            "4697037",
            "HZ160",
            "HZ160R",
            "MZ201",
            "MZ202",
            "MZ203",
            "MZ204",
            "MZ206",
            "i0020001",
            "i0020002",
            "i0020003",
            "i0020004",
            "i0030001",
            "i0030002",
            "i0030003",
            "i0030004",
            "i0040001",
            "i0040002",
            "i0040003",
            "i0040004",
            "i0070001",
            "i0070002",
            "i0070003",
            "i0070004",
            "i0250001",
            "i0250002",
            "i0260001",
            "i0260002",
            "i0670001",
            "i0670002",
            "i0670003",
            "i0670004",
            "i0680001",
            "i0680003",
            "i0680004",
            "i0690001",
            "i0690002",
            "i0690003",
            "i0690004",
            "i0700001",
            "i0700002",
            "i0700003",
            "i0700004",
            "i0710001",
            "i0710002",
            "i0710003",
            "i0710004",
            "i0780001",
            "i0780002",
            "i081016",
            "i081017",
            "i081018",
            "i081019",
            "i081020",
            "i081021",
            "i081022",
            "i081023",
            "i081024",
            "i091102",
            "i091103",
            "i091104",
            "p004024",
            "p004027",
            "p004031",
            "p004032",
            "p042100",
            "p042101",
            "p042103",
            "p042104",
            "p087111",
            "p087112",
            "p087113",
            "p087114",
            "p087115",
            "p1042105",
            "p1042106",
            "p1042107",
            "p1042109",
            "s1042100",
            "s1042101",
            "s1042103",
            "s1042104",
        ),
    ),
    (
        "cabletrays",
        "Хомути (стяжки кабельні)",
        (
            "A0150090019",
            "A0150090028",
            "A0150090029",
            "A0150090030",
            "A0150090050",
            "A0150090051",
            "A0150090075",
            "A0150090076",
            "A0150090077",
            "A0150090174",
            "A0150090175",
        ),
    ),
    (
        "other",
        "Професійний інструмент",
        (
            "s023301",
            "s080001",
            "s080002",
            "t007002",
            "t007003",
        ),
    ),
)


def upgrade() -> None:
    op.create_table(
        "product_categories_before_reviewed_taxonomy",
        sa.Column("product_id", sa.Uuid(), primary_key=True),
        sa.Column("category_id", sa.Uuid()),
        sa.Column("subcategory_id", sa.Uuid()),
    )
    op.create_table(
        "subcategory_before_avr_move",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(96), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    connection = op.get_bind()
    source = connection.execute(
        sa.text(
            "SELECT s.id FROM subcategories s JOIN categories c ON c.id = s.category_id "
            "WHERE c.slug = 'panels' AND s.name = :name"
        ),
        {"name": "\u0410\u0412\u0420 (автоматичний ввід резерву)"},
    ).scalar_one_or_none()
    category_id = connection.execute(
        sa.text("SELECT id FROM categories WHERE slug = 'lowvoltage'")
    ).scalar_one_or_none()
    if source is not None and category_id is not None:
        connection.execute(
            sa.text(
                "INSERT INTO subcategory_before_avr_move SELECT id, category_id, slug, name, position, is_active, created_at, updated_at "
                "FROM subcategories WHERE id = :id"
            ),
            {"id": source},
        )
        target = connection.execute(
            sa.text(
                "SELECT id FROM subcategories WHERE category_id = :category_id AND name = :name"
            ),
            {
                "category_id": category_id,
                "name": "\u0410\u0412\u0420 (автоматичний ввід резерву)",
            },
        ).scalar_one_or_none()
        connection.execute(
            sa.text(
                "INSERT INTO product_categories_before_reviewed_taxonomy "
                "SELECT id, category_id, subcategory_id FROM products WHERE subcategory_id = :id"
            ),
            {"id": source},
        )
        if target is None:
            target = source
            connection.execute(
                sa.text(
                    "UPDATE subcategories SET category_id = :category_id, slug = 'lowvoltage-17', position = 16 WHERE id = :id"
                ),
                {"category_id": category_id, "id": source},
            )
        connection.execute(
            sa.text(
                "UPDATE products SET category_id = :category_id, subcategory_id = :target WHERE subcategory_id = :source"
            ),
            {"category_id": category_id, "target": target, "source": source},
        )
        if target != source:
            connection.execute(
                sa.text("DELETE FROM subcategories WHERE id = :id"), {"id": source}
            )

    for category, subcategory, skus in REVIEWED_MOVES:
        destination = connection.execute(
            sa.text(
                "SELECT c.id, s.id FROM categories c JOIN subcategories s ON s.category_id = c.id "
                "WHERE c.slug = :category AND s.name = :subcategory"
            ),
            {"category": category, "subcategory": subcategory},
        ).one_or_none()
        if destination is None:
            continue  # An unseeded database gets these definitions from catalog.json.
        values = {
            "skus": skus,
            "category_id": destination[0],
            "subcategory_id": destination[1],
        }
        selection = "sku IN :skus AND (category_id IS DISTINCT FROM :category_id OR subcategory_id IS DISTINCT FROM :subcategory_id)"
        connection.execute(
            sa.text(
                "INSERT INTO product_categories_before_reviewed_taxonomy "
                "SELECT id, category_id, subcategory_id FROM products WHERE "
                + selection
                + " ON CONFLICT (product_id) DO NOTHING"
            ).bindparams(sa.bindparam("skus", expanding=True)),
            values,
        )
        connection.execute(
            sa.text(
                "UPDATE products SET category_id = :category_id, subcategory_id = :subcategory_id WHERE "
                + selection
            ).bindparams(sa.bindparam("skus", expanding=True)),
            values,
        )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "INSERT INTO subcategories (id, category_id, slug, name, position, is_active, created_at, updated_at) "
            "SELECT id, category_id, slug, name, position, is_active, created_at, updated_at FROM subcategory_before_avr_move "
            "ON CONFLICT (id) DO UPDATE SET category_id = EXCLUDED.category_id, slug = EXCLUDED.slug, name = EXCLUDED.name, position = EXCLUDED.position, is_active = EXCLUDED.is_active"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE products p SET category_id = b.category_id, subcategory_id = b.subcategory_id "
            "FROM product_categories_before_reviewed_taxonomy b WHERE p.id = b.product_id"
        )
    )
    op.drop_table("subcategory_before_avr_move")
    op.drop_table("product_categories_before_reviewed_taxonomy")
