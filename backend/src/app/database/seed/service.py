import json
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.modules.catalog.enums import ProductBadge, StockStatus
from app.api.modules.catalog.models import (
    Category,
    Product,
    ProductAttribute,
    ProductReview,
    Subcategory,
)
from app.api.modules.checkout.models import Promotion

CATALOG_DATA_PATH = Path(__file__).with_name("catalog.json")


def load_catalog_data() -> dict[str, Any]:
    data = json.loads(CATALOG_DATA_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Catalog seed root must be an object")
    return cast(dict[str, Any], data)


async def seed_database(session: AsyncSession) -> None:
    data = load_catalog_data()
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

    promotion = (
        await session.execute(select(Promotion).where(Promotion.code == "ZNIZKA10"))
    ).scalar_one_or_none()
    if promotion is None:
        session.add(Promotion(code="ZNIZKA10", discount_rate=Decimal("0.10")))
    await session.commit()
