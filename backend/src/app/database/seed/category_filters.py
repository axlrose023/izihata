import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.modules.catalog.enums import AttributeValueType, ProductAttributeSource
from app.api.modules.catalog.models import (
    CatalogAttribute,
    Category,
    CategoryAttribute,
    Product,
    ProductAttribute,
)

FILTER_DATA_PATH = Path(__file__).with_name("category_filters.json")


@dataclass(frozen=True)
class CategoryFilterSetup:
    attributes_created: int
    assignments_created: int
    categories: list[str]


async def configure_category_filters(
    session: AsyncSession, *, dry_run: bool = True
) -> CategoryFilterSetup:
    configuration = cast(
        dict[str, list[str]], json.loads(FILTER_DATA_PATH.read_text(encoding="utf-8"))
    )
    names = {name for keys in configuration.values() for name in keys}
    categories = {
        category.slug: category
        for category in (
            await session.scalars(
                select(Category).where(
                    Category.slug.in_(configuration), Category.is_active.is_(True)
                )
            )
        ).all()
    }
    observed = set(
        (
            await session.execute(
                select(Product.category_id, ProductAttribute.key)
                .join(ProductAttribute, ProductAttribute.product_id == Product.id)
                .where(
                    Product.is_active.is_(True),
                    Product.category_id.in_([c.id for c in categories.values()]),
                    ProductAttribute.source == ProductAttributeSource.PRIMARY,
                    ProductAttribute.key.in_(names),
                )
                .distinct()
            )
        ).all()
    )
    definitions: dict[str, CatalogAttribute] = {}
    for existing_definition in (
        await session.scalars(
            select(CatalogAttribute).order_by(
                CatalogAttribute.is_active.desc(),
                CatalogAttribute.position,
                CatalogAttribute.id,
            )
        )
    ).all():
        definitions.setdefault(existing_definition.name, existing_definition)
    assigned = {
        (assignment.category_id, assignment.attribute_id)
        for assignment in (await session.scalars(select(CategoryAttribute))).all()
    }
    new_definitions: list[CatalogAttribute] = []
    new_assignments: list[CategoryAttribute] = []
    configured: list[str] = []
    for slug, keys in configuration.items():
        category = categories.get(slug)
        if category is None:
            continue
        for position, name in enumerate(keys):
            if (category.id, name) not in observed:
                continue
            if slug not in configured:
                configured.append(slug)
            definition = definitions.get(name)
            if definition is None:
                definition = CatalogAttribute(
                    id=uuid4(),
                    code=f"filter_{hashlib.sha256(name.encode()).hexdigest()[:24]}",
                    name=name,
                    value_type=AttributeValueType.SELECT,
                    is_filterable=True,
                    is_active=True,
                    position=position,
                )
                definitions[name] = definition
                new_definitions.append(definition)
            if (category.id, definition.id) not in assigned:
                new_assignments.append(
                    CategoryAttribute(
                        category_id=category.id,
                        attribute_id=definition.id,
                        is_required=False,
                        is_primary_filter=True,
                        position=position,
                    )
                )
    if not dry_run:
        session.add_all(new_definitions)
        session.add_all(new_assignments)
        await session.flush()
    return CategoryFilterSetup(
        attributes_created=len(new_definitions),
        assignments_created=len(new_assignments),
        categories=configured,
    )
