from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.api.modules.catalog.enums import ProductBadge, ProductSort, StockStatus
from app.api.modules.catalog.models import (
    Category,
    Product,
    ProductAttribute,
    ProductReview,
    Subcategory,
)
from app.api.modules.catalog.schema import ProductListParams


class CategoryGateway:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_active(self) -> Sequence[Category]:
        stmt = (
            select(Category)
            .where(Category.is_active.is_(True))
            .options(selectinload(Category.subcategories))
            .order_by(Category.position, Category.name)
        )
        result = await self._session.execute(stmt)
        return result.scalars().unique().all()

    async def get_active_by_id(self, category_id: UUID) -> Category | None:
        stmt = select(Category).where(
            Category.id == category_id,
            Category.is_active.is_(True),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_active_subcategory_by_id(
        self,
        subcategory_id: UUID,
    ) -> Subcategory | None:
        stmt = select(Subcategory).where(
            Subcategory.id == subcategory_id,
            Subcategory.is_active.is_(True),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def product_counts(self) -> dict[UUID, int]:
        stmt = (
            select(Product.category_id, func.count(Product.id))
            .where(Product.is_active.is_(True))
            .group_by(Product.category_id)
        )
        result = await self._session.execute(stmt)
        return {category_id: int(count) for category_id, count in result.all()}

    async def subcategory_product_counts(self) -> dict[UUID, int]:
        stmt = (
            select(Product.subcategory_id, func.count(Product.id))
            .where(
                Product.is_active.is_(True),
                Product.subcategory_id.is_not(None),
            )
            .group_by(Product.subcategory_id)
        )
        result = await self._session.execute(stmt)
        return {
            subcategory_id: int(count)
            for subcategory_id, count in result.all()
            if subcategory_id is not None
        }


class ProductGateway:
    def __init__(self, session: AsyncSession):
        self._session = session

    def _conditions(
        self,
        params: ProductListParams,
        *,
        include_brands: bool = True,
        include_specs: bool = True,
    ) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = [Product.is_active.is_(True)]
        if params.product_ids:
            conditions.append(Product.id.in_(params.product_ids))
        if params.search:
            pattern = f"%{params.search.strip()}%"
            conditions.append(
                or_(
                    Product.name.ilike(pattern),
                    Product.brand.ilike(pattern),
                    Product.sku.ilike(pattern),
                )
            )
        if params.category:
            conditions.append(Product.category.has(Category.slug == params.category))
        if params.subcategory:
            conditions.append(
                Product.subcategory.has(Subcategory.slug == params.subcategory)
            )
        if include_brands and params.brand:
            conditions.append(Product.brand.in_(params.brand))
        if params.in_stock:
            conditions.append(Product.stock_status == StockStatus.IN_STOCK)
        if params.min_price is not None:
            conditions.append(Product.price >= params.min_price)
        if params.max_price is not None:
            conditions.append(Product.price <= params.max_price)
        if include_specs:
            for key, values in params.spec_filters.items():
                conditions.append(
                    Product.attributes.any(
                        and_(
                            ProductAttribute.key == key,
                            ProductAttribute.value.in_(values),
                        )
                    )
                )
        return conditions

    def _ordered(self, stmt: Select, sort: ProductSort) -> Select:
        if sort == ProductSort.PRICE_ASC:
            return stmt.order_by(Product.price.asc(), Product.id)
        if sort == ProductSort.PRICE_DESC:
            return stmt.order_by(Product.price.desc(), Product.id)
        if sort == ProductSort.NEWEST:
            return stmt.order_by(Product.created_at.desc(), Product.id)
        top_first = case((Product.badge == ProductBadge.TOP, 0), else_=1)
        return stmt.order_by(
            top_first,
            Product.reviews_count.desc(),
            Product.position,
            Product.id,
        )

    async def list(self, params: ProductListParams) -> Sequence[Product]:
        stmt = (
            select(Product)
            .where(*self._conditions(params))
            .options(
                joinedload(Product.category),
                joinedload(Product.subcategory),
                selectinload(Product.attributes),
            )
            .offset(params.offset)
            .limit(params.page_size)
        )
        result = await self._session.execute(self._ordered(stmt, params.sort))
        return result.scalars().unique().all()

    async def count(self, params: ProductListParams) -> int:
        stmt = select(func.count(Product.id)).where(*self._conditions(params))
        return int((await self._session.execute(stmt)).scalar_one())

    async def brand_facets(
        self,
        params: ProductListParams,
    ) -> Sequence[tuple[str, int]]:
        stmt = (
            select(Product.brand, func.count(Product.id))
            .where(*self._conditions(params, include_brands=False))
            .group_by(Product.brand)
            .order_by(Product.brand)
        )
        return [
            (brand, int(count))
            for brand, count in (await self._session.execute(stmt)).all()
        ]

    async def attribute_facets(
        self,
        params: ProductListParams,
    ) -> Sequence[tuple[str, str, int]]:
        stmt = (
            select(
                ProductAttribute.key,
                ProductAttribute.value,
                func.count(ProductAttribute.product_id),
            )
            .join(Product, Product.id == ProductAttribute.product_id)
            .where(*self._conditions(params, include_specs=False))
            .group_by(ProductAttribute.key, ProductAttribute.value)
            .order_by(ProductAttribute.key, ProductAttribute.value)
        )
        return [
            (key, value, int(count))
            for key, value, count in (await self._session.execute(stmt)).all()
        ]

    async def price_facet(
        self,
        params: ProductListParams,
    ) -> tuple[Decimal | None, Decimal | None]:
        stmt = select(func.min(Product.price), func.max(Product.price)).where(
            *self._conditions(params)
        )
        row = (await self._session.execute(stmt)).one()
        return row[0], row[1]

    async def get_by_id_for_update(self, product_id: UUID) -> Product | None:
        stmt = (
            select(Product)
            .where(Product.id == product_id, Product.is_active.is_(True))
            .options(
                joinedload(Product.category),
                joinedload(Product.subcategory),
                selectinload(Product.attributes),
            )
            .with_for_update(of=Product)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def identity_conflict(
        self,
        sku: str,
        slug: str,
        *,
        exclude_product_id: UUID | None = None,
    ) -> str | None:
        conditions = [or_(Product.sku == sku, Product.slug == slug)]
        if exclude_product_id is not None:
            conditions.append(Product.id != exclude_product_id)
        stmt = select(Product.sku, Product.slug).where(*conditions)
        for existing_sku, existing_slug in (await self._session.execute(stmt)).all():
            if existing_sku == sku:
                return "sku"
            if existing_slug == slug:
                return "slug"
        return None

    async def next_position(self) -> int:
        stmt = select(func.coalesce(func.max(Product.position), -1) + 1)
        return int((await self._session.execute(stmt)).scalar_one())

    async def create(self, product: Product) -> Product:
        self._session.add(product)
        await self._session.flush()
        return product

    async def get_by_slug(self, slug: str) -> Product | None:
        stmt = (
            select(Product)
            .where(Product.slug == slug, Product.is_active.is_(True))
            .options(
                joinedload(Product.category),
                joinedload(Product.subcategory),
                selectinload(Product.attributes),
                selectinload(Product.reviews),
            )
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_featured_reviews(self, limit: int = 3) -> Sequence[ProductReview]:
        stmt = (
            select(ProductReview)
            .join(Product, Product.id == ProductReview.product_id)
            .where(
                ProductReview.is_published.is_(True),
                ProductReview.is_featured.is_(True),
                Product.is_active.is_(True),
            )
            .order_by(ProductReview.created_at.desc(), ProductReview.id)
            .limit(limit)
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def get_many(self, product_ids: set[UUID]) -> Sequence[Product]:
        if not product_ids:
            return []
        stmt = select(Product).where(
            Product.id.in_(product_ids),
            Product.is_active.is_(True),
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def exists_active(self, product_id: UUID) -> bool:
        stmt = select(Product.id).where(
            Product.id == product_id,
            Product.is_active.is_(True),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def update(self, product: Product) -> Product:
        await self._session.flush()
        return product
