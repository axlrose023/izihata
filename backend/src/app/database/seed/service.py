import json
from decimal import Decimal
from pathlib import Path
from typing import Any, TypedDict, cast
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.modules.catalog.enums import (
    ProductBadge,
    ProductDocumentKind,
    ProductRelationKind,
    SaleUnit,
    StockStatus,
)
from app.api.modules.catalog.models import (
    Brand,
    CatalogSection,
    Category,
    Product,
    ProductAttribute,
    ProductDocument,
    ProductMedia,
    ProductRelation,
    ProductReview,
    Subcategory,
)
from app.api.modules.catalog.utils import slugify
from app.api.modules.checkout.models import Promotion

CATALOG_DATA_PATH = Path(__file__).with_name("catalog.json")


class SeedSection(TypedDict):
    slug: str
    name: str
    description: str
    categories: set[str]


SECTION_DATA: tuple[SeedSection, ...] = (
    {
        "slug": "home-repair",
        "name": "Дім і ремонт",  # noqa: RUF001
        "description": "Електрика для ремонту, побуту та розумного дому.",
        "categories": {
            "sockets",
            "lowvoltage",
            "relay",
            "switching",
            "cabletrays",
            "installation",
            "panels",
            "light",
            "metering",
            "smarthome",
        },
    },
    {
        "slug": "business-objects",
        "name": "Бізнес і об’єкти",  # noqa: RUF001
        "description": "Рішення для електромонтажу, комерційних та промислових об’єктів.",  # noqa: RUF001
        "categories": {"cable", "heating", "hv", "grounding", "network", "other"},
    },
    {
        "slug": "energy-independence",
        "name": "Енергонезалежність",
        "description": "Резервне живлення, опалення та зарядна інфраструктура.",
        "categories": {"power", "evcharge"},
    },
)


def load_catalog_data() -> dict[str, Any]:
    data = json.loads(CATALOG_DATA_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Catalog seed root must be an object")
    return cast(dict[str, Any], data)


async def seed_database(session: AsyncSession) -> None:
    data = load_catalog_data()
    sections = {
        section.slug: section
        for section in (await session.execute(select(CatalogSection))).scalars().all()
    }
    category_sections: dict[str, CatalogSection] = {}
    for position, raw_section in enumerate(SECTION_DATA):
        section = sections.get(raw_section["slug"])
        if section is None:
            section = CatalogSection(
                slug=raw_section["slug"],
                name=raw_section["name"],
                description=raw_section["description"],
                position=position,
            )
            session.add(section)
            await session.flush()
            sections[section.slug] = section
        for category_slug in raw_section["categories"]:
            category_sections[category_slug] = section

    categories = {
        category.slug: category
        for category in (await session.execute(select(Category))).scalars().all()
    }
    subcategories = {
        (subcategory.category_id, subcategory.name): subcategory
        for subcategory in (await session.execute(select(Subcategory))).scalars().all()
    }

    for category_position, raw_category in enumerate(data["categories"]):
        slug = raw_category["id"]
        category = categories.get(slug)
        if category is None:
            category = Category(
                slug=slug,
                name=raw_category["name"],
                accent=raw_category["accent"],
                position=category_position,
            )
            session.add(category)
            await session.flush()
            categories[slug] = category
        category.name = raw_category["name"]
        category.accent = raw_category["accent"]
        category.position = category_position
        section = category_sections.get(slug)
        if section is not None:
            category.section_id = section.id

        for subcategory_position, name in enumerate(raw_category["subs"]):
            key = (category.id, name)
            if key in subcategories:
                continue
            subcategory = Subcategory(
                category_id=category.id,
                slug=f"{slug}-{subcategory_position + 1}",
                name=name,
                position=subcategory_position,
            )
            session.add(subcategory)
            subcategories[key] = subcategory
    await session.flush()

    products_by_sku = {
        product.sku: product
        for product in (await session.execute(select(Product))).scalars().all()
    }
    reviewed_product_ids = set(
        (await session.execute(select(ProductReview.product_id))).scalars().all()
    )
    review_templates = data["reviewTemplates"]
    for position, raw_product in enumerate(data["products"]):
        category_data = next(
            item for item in data["categories"] if item["id"] == raw_product["cat"]
        )
        image_url = category_data.get("imageUrl")
        existing_product = products_by_sku.get(raw_product["sku"])
        if existing_product is not None:
            existing_product.image_url = image_url
            product = existing_product
        else:
            category = categories[raw_product["cat"]]
            subcategory = subcategories[(category.id, raw_product["sub"])]
            product = Product(
                category_id=category.id,
                subcategory_id=subcategory.id,
                sku=raw_product["sku"],
                slug=raw_product["sku"].lower(),
                name=raw_product["name"],
                brand=raw_product["brand"],
                image_url=image_url,
                price=Decimal(str(raw_product["price"])),
                old_price=(
                    Decimal(str(raw_product["oldPrice"]))
                    if raw_product["oldPrice"] is not None
                    else None
                ),
                badge=(
                    ProductBadge(raw_product["badge"]) if raw_product["badge"] else None
                ),
                stock_status=(
                    StockStatus.IN_STOCK
                    if raw_product["stock"] == "in"
                    else StockStatus.PREORDER
                ),
                availability_days=0 if raw_product["stock"] == "in" else 5,
                rating=Decimal(str(raw_product["rating"])),
                reviews_count=raw_product["reviews"],
                position=position,
                attributes=[
                    ProductAttribute(key=key, value=value)
                    for key, value in raw_product["specs"].items()
                ],
            )
            session.add(product)
            await session.flush()
            products_by_sku[product.sku] = product

        if product.id not in reviewed_product_ids:
            first_index = position % len(review_templates)
            selected_reviews = (
                review_templates[first_index],
                review_templates[(first_index + 1) % len(review_templates)],
            )
            session.add_all(
                ProductReview(
                    product_id=product.id,
                    is_featured=position < 3 and review_index == 0,
                    **review,
                )
                for review_index, review in enumerate(selected_reviews)
            )
            reviewed_product_ids.add(product.id)

    await _seed_brands(session, products_by_sku)
    await _seed_catalog_demo_content(
        session, categories, subcategories, products_by_sku
    )

    promotion = (
        await session.execute(select(Promotion).where(Promotion.code == "ZNIZKA10"))
    ).scalar_one_or_none()
    if promotion is None:
        session.add(Promotion(code="ZNIZKA10", discount_rate=Decimal("0.10")))
    await session.commit()


async def _seed_brands(
    session: AsyncSession,
    products_by_sku: dict[str, Product],
) -> None:
    """Give every brand a row so the storefront can list manufacturers.

    Production gets these from the migration backfill; a freshly bootstrapped
    database needs them here.
    """
    known = set((await session.execute(select(Brand.name))).scalars().all())
    taken = set((await session.execute(select(Brand.slug))).scalars().all())
    position = len(known)
    for name in sorted({product.brand for product in products_by_sku.values()}):
        if name in known:
            continue
        base = slugify(name) or "brand"
        slug, suffix = base, 2
        while slug in taken:
            slug = f"{base}-{suffix}"
            suffix += 1
        taken.add(slug)
        session.add(Brand(slug=slug, name=name, position=position, is_active=True))
        position += 1
    await session.flush()


async def _seed_catalog_demo_content(
    session: AsyncSession,
    categories: dict[str, Category],
    subcategories: dict[tuple[UUID, str], Subcategory],
    products_by_sku: dict[str, Product],
) -> None:
    sku = "DEMO-MCB-16"
    category = categories["lowvoltage"]
    subcategory_name = "Автоматичні вимикачі (модульні / корпусні / повітряні)"
    subcategory = subcategories[(category.id, subcategory_name)]
    product = products_by_sku.get(sku)
    if product is None:
        product = Product(
            category_id=category.id,
            subcategory_id=subcategory.id,
            sku=sku,
            slug="demo-modular-circuit-breaker-1p-c16",
            name="Демо: модульний автоматичний вимикач 1P C16",
            brand="Demo Electric",
            brand_country="Україна",
            production_country="Китай",
            short_description="Демонстраційна позиція з повним набором даних картки товару.",
            description=(
                "Тестовий товар для перевірки галереї, документації, гуртових умов "
                "та структурованих характеристик. Не призначений для продажу."  # noqa: RUF001
            ),
            image_url="/product-images/demo/circuit-breaker-front.webp",
            price=Decimal("320.00"),
            old_price=Decimal("370.00"),
            badge=ProductBadge.RECOMMENDED,
            stock_status=StockStatus.IN_STOCK_TODAY,
            availability_days=0,
            sale_unit=SaleUnit.PIECE,
            wholesale_price=Decimal("280.00"),
            wholesale_min_quantity=5,
            rating=Decimal("0"),
            reviews_count=0,
            position=10000,
            attributes=[
                ProductAttribute(key="Полюси", value="1P"),
                ProductAttribute(key="Номінал", value="16 А"),  # noqa: RUF001
                ProductAttribute(key="Характеристика", value="C"),
                ProductAttribute(key="Відключ. здатність", value="6 кА"),
                ProductAttribute(key="Напруга", value="230 В"),  # noqa: RUF001
                ProductAttribute(key="Серія", value="Demo Modular"),
            ],
        )
        session.add(product)
        await session.flush()
        products_by_sku[sku] = product

    has_media = await session.scalar(
        select(exists().where(ProductMedia.product_id == product.id))
    )
    if not has_media:
        session.add_all(
            (
                ProductMedia(
                    product_id=product.id,
                    url="/product-images/demo/circuit-breaker-front.webp",
                    alt="Демонстраційний модульний автоматичний вимикач, вигляд спереду",
                    position=0,
                ),
                ProductMedia(
                    product_id=product.id,
                    url="/product-images/demo/circuit-breaker-side.webp",
                    alt="Демонстраційний модульний автоматичний вимикач, вигляд збоку",
                    position=1,
                ),
            )
        )
    has_document = await session.scalar(
        select(exists().where(ProductDocument.product_id == product.id))
    )
    if not has_document:
        session.add(
            ProductDocument(
                product_id=product.id,
                kind=ProductDocumentKind.DATASHEET,
                title="Технічна специфікація (демо)",
                url="/documents/demo-circuit-breaker-specification.pdf",
                position=0,
            )
        )

    # Curated relations: "bought together" is admin-managed, never inferred,
    # so the demo catalog has to carry a couple of them to be representative.
    demo_relations = (
        ("AX-10001", ProductRelationKind.ALTERNATIVE, 0),
        ("AX-10006", ProductRelationKind.BOUGHT_TOGETHER, 0),
        ("AX-10003", ProductRelationKind.BOUGHT_TOGETHER, 1),
    )
    for target_sku, kind, position in demo_relations:
        target = products_by_sku.get(target_sku)
        if target is None or target.id == product.id:
            continue
        has_relation = await session.scalar(
            select(
                exists().where(
                    ProductRelation.source_product_id == product.id,
                    ProductRelation.target_product_id == target.id,
                    ProductRelation.kind == kind,
                )
            )
        )
        if not has_relation:
            session.add(
                ProductRelation(
                    source_product_id=product.id,
                    target_product_id=target.id,
                    kind=kind,
                    position=position,
                )
            )
