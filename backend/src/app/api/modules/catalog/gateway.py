from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, and_, case, delete, func, or_, select, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.api.modules.catalog.enums import (
    ProductAttributeSource,
    ProductBadge,
    ProductRelationKind,
    ProductSort,
    StockStatus,
    StockSubscriptionStatus,
)
from app.api.modules.catalog.models import (
    Brand,
    CatalogAttribute,
    CatalogSection,
    Category,
    CategoryAttribute,
    Product,
    ProductAttribute,
    ProductRelation,
    ProductReview,
    ProductStockSubscription,
    Subcategory,
)
from app.api.modules.catalog.schema import (
    AdminProductListParams,
    ProductListParams,
    SpecFacetParams,
)


class BrandGateway:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list(self, *, only_active: bool) -> Sequence[Brand]:
        stmt = select(Brand).order_by(Brand.position, Brand.name)
        if only_active:
            stmt = stmt.where(Brand.is_active.is_(True))
        return (await self._session.execute(stmt)).scalars().all()

    async def get_by_id(
        self, brand_id: UUID, *, for_update: bool = False
    ) -> Brand | None:
        stmt = select(Brand).where(Brand.id == brand_id)
        if for_update:
            stmt = stmt.with_for_update()
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Brand | None:
        stmt = select(Brand).where(Brand.slug == slug, Brand.is_active.is_(True))
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_name(self, name: str) -> Brand | None:
        stmt = select(Brand).where(Brand.name == name)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def slug_taken(self, slug: str) -> bool:
        stmt = select(Brand.id).where(Brand.slug == slug)
        return (await self._session.execute(stmt)).first() is not None

    async def create(self, brand: Brand) -> Brand:
        self._session.add(brand)
        await self._session.flush()
        return brand

    async def next_position(self) -> int:
        stmt = select(func.coalesce(func.max(Brand.position), -1) + 1)
        return int((await self._session.execute(stmt)).scalar_one())

    async def product_count(self, name: str) -> int:
        return int(
            (
                await self._session.execute(
                    select(func.count(Product.id)).where(
                        Product.brand == name, Product.is_active.is_(True)
                    )
                )
            ).scalar_one()
        )

    async def product_counts(self) -> dict[str, int]:
        stmt = (
            select(Product.brand, func.count(Product.id))
            .where(Product.is_active.is_(True))
            .group_by(Product.brand)
        )
        return {
            name: int(count)
            for name, count in (await self._session.execute(stmt)).all()
        }


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

    async def list_active_sections(self) -> Sequence[CatalogSection]:
        stmt = (
            select(CatalogSection)
            .where(CatalogSection.is_active.is_(True))
            .options(
                selectinload(CatalogSection.categories).selectinload(
                    Category.subcategories
                )
            )
            .order_by(CatalogSection.position, CatalogSection.name)
        )
        return (await self._session.execute(stmt)).scalars().unique().all()

    async def get_active_by_id(self, category_id: UUID) -> Category | None:
        stmt = select(Category).where(
            Category.id == category_id,
            Category.is_active.is_(True),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_id_for_update(self, category_id: UUID) -> Category | None:
        stmt = select(Category).where(Category.id == category_id).with_for_update()
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_section_by_slug(self, slug: str) -> CatalogSection | None:
        stmt = select(CatalogSection).where(CatalogSection.slug == slug)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_section_for_update(self, section_id: UUID) -> CatalogSection | None:
        stmt = (
            select(CatalogSection)
            .where(CatalogSection.id == section_id)
            .with_for_update()
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def create_section(self, section: CatalogSection) -> CatalogSection:
        self._session.add(section)
        await self._session.flush()
        return section

    async def list_attributes(self) -> Sequence[CatalogAttribute]:
        stmt = (
            select(CatalogAttribute)
            .where(CatalogAttribute.is_active.is_(True))
            .order_by(CatalogAttribute.position, CatalogAttribute.name)
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def get_attributes_by_ids(
        self,
        attribute_ids: set[UUID],
    ) -> Sequence[CatalogAttribute]:
        if not attribute_ids:
            return []
        stmt = select(CatalogAttribute).where(
            CatalogAttribute.id.in_(attribute_ids),
            CatalogAttribute.is_active.is_(True),
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def get_attribute_by_code(self, code: str) -> CatalogAttribute | None:
        stmt = select(CatalogAttribute).where(CatalogAttribute.code == code)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def create_attribute(self, attribute: CatalogAttribute) -> CatalogAttribute:
        self._session.add(attribute)
        await self._session.flush()
        return attribute

    async def replace_category_attributes(
        self,
        category_id: UUID,
        assignments: list[CategoryAttribute],
    ) -> None:
        await self._session.execute(
            delete(CategoryAttribute).where(
                CategoryAttribute.category_id == category_id
            )
        )
        self._session.add_all(assignments)
        await self._session.flush()

    async def list_category_attributes(
        self,
        category_id: UUID,
    ) -> Sequence[tuple[CategoryAttribute, CatalogAttribute]]:
        stmt = (
            select(CategoryAttribute, CatalogAttribute)
            .join(
                CatalogAttribute, CatalogAttribute.id == CategoryAttribute.attribute_id
            )
            .where(CategoryAttribute.category_id == category_id)
            .order_by(CategoryAttribute.position, CatalogAttribute.name)
        )
        return [
            (assignment, attribute)
            for assignment, attribute in (await self._session.execute(stmt)).all()
        ]

    async def get_active_subcategory_by_id(
        self,
        subcategory_id: UUID,
    ) -> Subcategory | None:
        stmt = select(Subcategory).where(
            Subcategory.id == subcategory_id,
            Subcategory.is_active.is_(True),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def category_and_subcategory_product_counts(
        self,
    ) -> tuple[dict[UUID, int], dict[UUID, int]]:
        stmt = (
            select(Product.category_id, Product.subcategory_id, func.count(Product.id))
            .where(Product.is_active.is_(True))
            .group_by(Product.category_id, Product.subcategory_id)
        )
        category_counts: dict[UUID, int] = {}
        subcategory_counts: dict[UUID, int] = {}
        for category_id, subcategory_id, count in (
            await self._session.execute(stmt)
        ).all():
            category_counts[category_id] = category_counts.get(category_id, 0) + int(
                count
            )
            if subcategory_id is not None:
                subcategory_counts[subcategory_id] = int(count)
        return category_counts, subcategory_counts

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

    async def _filterable_attribute_conditions(
        self, params: ProductListParams
    ) -> list[ColumnElement[bool]]:
        metadata = (
            await self._session.execute(
                select(
                    CategoryAttribute.category_id,
                    CatalogAttribute.name,
                    Category.slug,
                    CatalogAttribute.is_active,
                    CatalogAttribute.is_filterable,
                )
                .join(
                    CatalogAttribute,
                    CatalogAttribute.id == CategoryAttribute.attribute_id,
                )
                .join(Category, Category.id == CategoryAttribute.category_id)
            )
        ).all()
        if not metadata:
            return []
        configured = select(CategoryAttribute.category_id)
        filterable = (
            select(CategoryAttribute.category_id, CatalogAttribute.name)
            .join(
                CatalogAttribute, CatalogAttribute.id == CategoryAttribute.attribute_id
            )
            .where(
                CatalogAttribute.is_active.is_(True),
                CatalogAttribute.is_filterable.is_(True),
            )
        )
        # Imported attributes retain their original keys and need no backfill.
        # New/unconfigured categories keep the existing paginated fallback.
        conditions = [
            or_(
                Product.category_id.not_in(configured),
                tuple_(Product.category_id, ProductAttribute.key).in_(filterable),
            )
        ]
        unconfigured_product = await self._session.scalar(
            select(Product.id)
            .where(
                *self._conditions(params, include_specs=False),
                Product.category_id.not_in(configured),
            )
            .limit(1)
        )
        if unconfigured_product is None:
            # Limit the covering-index scan to candidate keys. The category/key
            # membership above still prevents leaking another category's fields.
            names = {
                name
                for _, name, slug, active, enabled in metadata
                if active
                and enabled
                and (not params.category or slug == params.category)
            }
            conditions.append(ProductAttribute.key.in_(names))
        return conditions

    def _spec_filter_conditions(
        self,
        params: ProductListParams,
        *,
        include_facet_key: bool = False,
        exclude_key: str | None = None,
    ) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = []
        for key, values in params.spec_filters.items():
            if key == exclude_key:
                continue
            matching_value = Product.attributes.any(
                and_(
                    ProductAttribute.key == key,
                    ProductAttribute.value.in_(values),
                )
            )
            conditions.append(
                or_(ProductAttribute.key == key, matching_value)
                if include_facet_key
                else matching_value
            )
        return conditions

    def _conditions(
        self,
        params: ProductListParams,
        *,
        include_brands: bool = True,
        include_specs: bool = True,
        include_price: bool = True,
        include_availability: bool = True,
        include_sale_unit: bool = True,
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
        if params.section:
            conditions.append(
                Product.category.has(
                    Category.section.has(CatalogSection.slug == params.section)
                )
            )
        if params.badge:
            conditions.append(Product.badge.in_(params.badge))
        if params.is_popular:
            conditions.append(Product.is_popular.is_(True))
        if params.subcategory:
            conditions.append(
                Product.subcategory.has(Subcategory.slug == params.subcategory)
            )
        if include_brands and params.brand:
            conditions.append(Product.brand.in_(params.brand))
        if include_availability and params.in_stock:
            conditions.append(
                Product.stock_status.in_(
                    [StockStatus.IN_STOCK_TODAY, StockStatus.IN_STOCK]
                )
            )
        if include_availability and params.availability:
            conditions.append(Product.stock_status.in_(params.availability))
        if include_sale_unit and params.sale_unit:
            conditions.append(Product.sale_unit.in_(params.sale_unit))
        if include_price and params.min_price is not None:
            conditions.append(Product.price >= params.min_price)
        if include_price and params.max_price is not None:
            conditions.append(Product.price <= params.max_price)
        if include_specs:
            conditions.extend(self._spec_filter_conditions(params))
        return conditions

    def _admin_conditions(
        self,
        params: AdminProductListParams,
    ) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = []
        if params.is_active is not None:
            conditions.append(Product.is_active.is_(params.is_active))
        if params.search:
            pattern = f"%{params.search.strip()}%"
            conditions.append(
                or_(
                    Product.name.ilike(pattern),
                    Product.brand.ilike(pattern),
                    Product.sku.ilike(pattern),
                )
            )
        return conditions

    def _ordered(
        self,
        stmt: Select,
        sort: ProductSort,
        *,
        exact_sku: str | None = None,
    ) -> Select:
        if sort == ProductSort.PRICE_ASC:
            return stmt.order_by(Product.price.asc(), Product.id)
        if sort == ProductSort.PRICE_DESC:
            return stmt.order_by(Product.price.desc(), Product.id)
        if sort == ProductSort.NEWEST:
            return stmt.order_by(Product.created_at.desc(), Product.id)
        if sort == ProductSort.REVIEWS:
            return stmt.order_by(
                Product.reviews_count.desc(),
                Product.rating.desc(),
                Product.id,
            )
        if sort == ProductSort.AVAILABILITY:
            availability_rank = case(
                (Product.stock_status == StockStatus.IN_STOCK_TODAY, 0),
                (Product.stock_status == StockStatus.IN_STOCK, 1),
                (Product.stock_status == StockStatus.PREORDER, 2),
                else_=3,
            )
            return stmt.order_by(availability_rank, Product.position, Product.id)
        popular_first = case((Product.is_popular.is_(True), 0), else_=1)
        top_first = case((Product.badge == ProductBadge.TOP, 0), else_=1)
        if exact_sku:
            exact_sku_first = case(
                (func.lower(Product.sku) == exact_sku.lower(), 0),
                else_=1,
            )
            return stmt.order_by(
                exact_sku_first,
                popular_first,
                top_first,
                Product.reviews_count.desc(),
                Product.position,
                Product.id,
            )
        return stmt.order_by(
            popular_first,
            top_first,
            Product.reviews_count.desc(),
            Product.position,
            Product.id,
        )

    async def list(self, params: ProductListParams) -> Sequence[Product]:
        # Sort/page narrow IDs before loading full product rows and relations.
        page_ids = (
            self._ordered(
                select(Product.id).where(*self._conditions(params)),
                params.sort,
                exact_sku=params.search,
            )
            .offset(params.offset)
            .limit(params.page_size)
            .subquery()
        )
        stmt = (
            select(Product)
            .join(page_ids, Product.id == page_ids.c.id)
            .options(
                joinedload(Product.category),
                joinedload(Product.subcategory),
                selectinload(
                    Product.attributes.and_(
                        ProductAttribute.source == ProductAttributeSource.PRIMARY
                    )
                ),
            )
        )
        result = await self._session.execute(
            self._ordered(stmt, params.sort, exact_sku=params.search)
        )
        return result.scalars().unique().all()

    async def count(self, params: ProductListParams) -> int:
        stmt = select(func.count(Product.id)).where(*self._conditions(params))
        return int((await self._session.execute(stmt)).scalar_one())

    async def list_for_admin(
        self,
        params: AdminProductListParams,
    ) -> Sequence[Product]:
        stmt = (
            select(Product)
            .where(*self._admin_conditions(params))
            .options(
                joinedload(Product.category),
                joinedload(Product.subcategory),
                selectinload(Product.attributes),
            )
            .order_by(Product.created_at.desc(), Product.id)
            .offset(params.offset)
            .limit(params.page_size)
        )
        return (await self._session.execute(stmt)).scalars().unique().all()

    async def count_for_admin(self, params: AdminProductListParams) -> int:
        stmt = select(func.count(Product.id)).where(*self._admin_conditions(params))
        return int((await self._session.execute(stmt)).scalar_one())

    async def list_active_slugs(self) -> Sequence[str]:
        stmt = (
            select(Product.slug)
            .where(Product.is_active.is_(True))
            .order_by(Product.slug)
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def get_by_sku(self, sku: str) -> Product | None:
        stmt = (
            select(Product)
            .where(Product.sku == sku)
            .options(
                joinedload(Product.category),
                joinedload(Product.subcategory),
                selectinload(Product.attributes),
            )
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def exact_search_id(self, search: str) -> UUID | None:
        stmt = (
            select(Product.id)
            .where(
                Product.is_active.is_(True), func.lower(Product.sku) == search.lower()
            )
            .limit(2)
        )
        matches = (await self._session.execute(stmt)).scalars().all()
        return matches[0] if len(matches) == 1 else None

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
                func.count(func.distinct(ProductAttribute.product_id)),
            )
            .join(Product, Product.id == ProductAttribute.product_id)
            .where(
                *self._conditions(params, include_specs=False),
                *self._spec_filter_conditions(params, include_facet_key=True),
                *await self._filterable_attribute_conditions(params),
            )
            .group_by(ProductAttribute.key, ProductAttribute.value)
            .order_by(ProductAttribute.key, ProductAttribute.value)
        )
        return [
            (key, value, int(count))
            for key, value, count in (await self._session.execute(stmt)).all()
        ]

    async def spec_facet_page(
        self, params: SpecFacetParams
    ) -> Sequence[tuple[str, int]]:
        if params.facet_key:
            column = ProductAttribute.value
            count = func.count(func.distinct(ProductAttribute.product_id))
            conditions = [ProductAttribute.key == params.facet_key]
            conditions.extend(
                self._spec_filter_conditions(params, exclude_key=params.facet_key)
            )
        else:
            column = ProductAttribute.key
            count = func.count(func.distinct(ProductAttribute.value))
            conditions = self._spec_filter_conditions(params, include_facet_key=True)
            conditions.extend(await self._filterable_attribute_conditions(params))
        if params.facet_search:
            conditions.append(column.ilike(f"%{params.facet_search}%"))
        stmt = (
            select(column, count)
            .join(Product, Product.id == ProductAttribute.product_id)
            .where(*self._conditions(params, include_specs=False), *conditions)
            .group_by(column)
            .order_by(column)
            .offset(params.offset)
            .limit(params.page_size + 1)
        )
        return [
            (value, int(count))
            for value, count in (await self._session.execute(stmt)).all()
        ]

    async def price_facet(
        self,
        params: ProductListParams,
    ) -> tuple[Decimal | None, Decimal | None]:
        stmt = select(func.min(Product.price), func.max(Product.price)).where(
            *self._conditions(params, include_price=False)
        )
        row = (await self._session.execute(stmt)).one()
        return row[0], row[1]

    async def availability_facets(
        self,
        params: ProductListParams,
    ) -> Sequence[tuple[StockStatus, int]]:
        stmt = (
            select(Product.stock_status, func.count(Product.id))
            .where(*self._conditions(params, include_availability=False))
            .group_by(Product.stock_status)
            .order_by(Product.stock_status)
        )
        return [
            (status, int(count))
            for status, count in (await self._session.execute(stmt)).all()
        ]

    async def sale_unit_facets(
        self,
        params: ProductListParams,
    ) -> Sequence[tuple[str, int]]:
        stmt = (
            select(Product.sale_unit, func.count(Product.id))
            .where(*self._conditions(params, include_sale_unit=False))
            .group_by(Product.sale_unit)
            .order_by(Product.sale_unit)
        )
        return [
            (sale_unit.value, int(count))
            for sale_unit, count in (await self._session.execute(stmt)).all()
        ]

    async def get_by_id(self, product_id: UUID) -> Product | None:
        stmt = (
            select(Product)
            .where(Product.id == product_id)
            .options(
                joinedload(Product.category),
                joinedload(Product.subcategory),
                selectinload(Product.attributes),
                selectinload(Product.media),
                selectinload(Product.documents),
            )
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_id_for_update(self, product_id: UUID) -> Product | None:
        stmt = (
            select(Product)
            .where(Product.id == product_id)
            .options(
                joinedload(Product.category),
                joinedload(Product.subcategory),
                selectinload(Product.attributes),
                selectinload(Product.media),
                selectinload(Product.documents),
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
            .execution_options(populate_existing=True)
            .options(
                joinedload(Product.category),
                joinedload(Product.subcategory),
                selectinload(Product.attributes),
                selectinload(Product.media),
                selectinload(Product.documents),
            )
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_active_id_and_review_count_by_slug(
        self,
        slug: str,
    ) -> tuple[UUID, int] | None:
        stmt = select(Product.id, Product.reviews_count).where(
            Product.slug == slug,
            Product.is_active.is_(True),
        )
        row = (await self._session.execute(stmt)).one_or_none()
        return (row[0], row[1]) if row is not None else None

    async def list_published_reviews(
        self,
        product_id: UUID,
        *,
        offset: int,
        limit: int,
    ) -> Sequence[ProductReview]:
        stmt = (
            select(ProductReview)
            .where(
                ProductReview.product_id == product_id,
                ProductReview.is_published.is_(True),
            )
            .order_by(ProductReview.created_at.desc(), ProductReview.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def list_related(
        self,
        source_product_id: UUID,
        kind: ProductRelationKind,
        *,
        limit: int = 8,
    ) -> Sequence[Product]:
        stmt = (
            select(Product)
            .join(
                ProductRelation,
                ProductRelation.target_product_id == Product.id,
            )
            .where(
                ProductRelation.source_product_id == source_product_id,
                ProductRelation.kind == kind,
                Product.is_active.is_(True),
            )
            .options(
                joinedload(Product.category),
                joinedload(Product.subcategory),
                selectinload(
                    Product.attributes.and_(
                        ProductAttribute.source == ProductAttributeSource.PRIMARY
                    )
                ),
            )
            .order_by(ProductRelation.position, Product.id)
            .limit(limit)
        )
        return (await self._session.execute(stmt)).scalars().unique().all()

    async def list_relations(
        self,
        source_product_id: UUID,
    ) -> Sequence[tuple[ProductRelation, Product]]:
        stmt = (
            select(ProductRelation, Product)
            .join(Product, Product.id == ProductRelation.target_product_id)
            .where(ProductRelation.source_product_id == source_product_id)
            .order_by(ProductRelation.kind, ProductRelation.position, Product.id)
        )
        return [
            (relation, product)
            for relation, product in (await self._session.execute(stmt)).all()
        ]

    async def list_related_to_any(
        self,
        source_product_ids: set[UUID],
        kind: ProductRelationKind,
        *,
        limit: int = 8,
    ) -> Sequence[Product]:
        """Products related to any of the given sources, excluding the sources."""
        if not source_product_ids:
            return []
        # Resolve the ordered target ids first: deduplicating in the same
        # statement would need DISTINCT or GROUP BY, and neither survives the
        # extra columns the eager loaders add to the select list.
        ranked = (
            select(
                ProductRelation.target_product_id,
                func.min(ProductRelation.position).label("relation_position"),
            )
            .join(Product, Product.id == ProductRelation.target_product_id)
            .where(
                ProductRelation.source_product_id.in_(source_product_ids),
                ProductRelation.target_product_id.not_in(source_product_ids),
                ProductRelation.kind == kind,
                Product.is_active.is_(True),
            )
            .group_by(ProductRelation.target_product_id)
            .order_by("relation_position", ProductRelation.target_product_id)
            .limit(limit)
        )
        ordered_ids = [row[0] for row in (await self._session.execute(ranked)).all()]
        if not ordered_ids:
            return []

        stmt = (
            select(Product)
            .where(Product.id.in_(ordered_ids))
            .options(
                joinedload(Product.category),
                joinedload(Product.subcategory),
                selectinload(Product.attributes),
            )
        )
        products = (await self._session.execute(stmt)).scalars().unique().all()
        by_id = {product.id: product for product in products}
        return [by_id[product_id] for product_id in ordered_ids if product_id in by_id]

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

    async def create_review(self, review: ProductReview) -> ProductReview:
        self._session.add(review)
        await self._session.flush()
        return review

    async def get_review_for_update(self, review_id: UUID) -> ProductReview | None:
        stmt = (
            select(ProductReview).where(ProductReview.id == review_id).with_for_update()
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_reviews(
        self,
        *,
        offset: int,
        limit: int,
    ) -> Sequence[tuple[ProductReview, Product]]:
        stmt = (
            select(ProductReview, Product)
            .join(Product, Product.id == ProductReview.product_id)
            .order_by(ProductReview.created_at.desc(), ProductReview.id)
            .offset(offset)
            .limit(limit)
        )
        return [
            (review, product)
            for review, product in (await self._session.execute(stmt)).all()
        ]

    async def review_count(self) -> int:
        stmt = select(func.count(ProductReview.id))
        return int((await self._session.execute(stmt)).scalar_one())

    async def refresh_review_summary(self, product_id: UUID) -> None:
        product = (
            await self._session.execute(
                select(Product).where(Product.id == product_id).with_for_update()
            )
        ).scalar_one_or_none()
        if product is None:
            return
        summary = await self._session.execute(
            select(func.count(ProductReview.id), func.avg(ProductReview.rating)).where(
                ProductReview.product_id == product_id,
                ProductReview.is_published.is_(True),
            )
        )
        count, rating = summary.one()
        product.reviews_count = int(count)
        product.rating = Decimal(str(rating or 0)).quantize(Decimal("0.1"))
        await self._session.flush()

    async def replace_relations(
        self,
        source_product_id: UUID,
        relations: Sequence[ProductRelation],
    ) -> None:
        await self._session.execute(
            delete(ProductRelation).where(
                ProductRelation.source_product_id == source_product_id
            )
        )
        self._session.add_all(relations)
        await self._session.flush()

    async def get_stock_subscription(
        self,
        product_id: UUID,
        email: str,
    ) -> ProductStockSubscription | None:
        stmt = select(ProductStockSubscription).where(
            ProductStockSubscription.product_id == product_id,
            ProductStockSubscription.email == email,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def create_stock_subscription(
        self,
        subscription: ProductStockSubscription,
    ) -> ProductStockSubscription:
        self._session.add(subscription)
        await self._session.flush()
        return subscription

    async def active_stock_subscriptions(
        self,
        product_id: UUID,
    ) -> Sequence[ProductStockSubscription]:
        stmt = select(ProductStockSubscription).where(
            ProductStockSubscription.product_id == product_id,
            ProductStockSubscription.status == StockSubscriptionStatus.ACTIVE,
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def mark_stock_subscription_notified(self, subscription_id: UUID) -> None:
        stmt = (
            update(ProductStockSubscription)
            .where(
                ProductStockSubscription.id == subscription_id,
                ProductStockSubscription.status == StockSubscriptionStatus.ACTIVE,
            )
            .values(status=StockSubscriptionStatus.NOTIFIED)
        )
        await self._session.execute(stmt)

    async def rename_brand(self, old_name: str, new_name: str) -> None:
        await self._session.execute(
            update(Product).where(Product.brand == old_name).values(brand=new_name)
        )

    async def get_many(self, product_ids: set[UUID]) -> Sequence[Product]:
        if not product_ids:
            return []
        stmt = select(Product).where(
            Product.id.in_(product_ids),
            Product.is_active.is_(True),
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def list_matching_attributes(
        self,
        *,
        category_slug: str,
        requirements: Sequence[tuple[set[str], set[str]]],
        limit: int = 8,
    ) -> Sequence[Product]:
        if not requirements or any(
            not keys or not values for keys, values in requirements
        ):
            return []
        stmt = (
            select(Product)
            .where(
                Product.is_active.is_(True),
                Product.stock_status != StockStatus.OUT_OF_STOCK,
                Product.category.has(Category.slug == category_slug),
                *(
                    Product.attributes.any(
                        and_(
                            ProductAttribute.key.in_(keys),
                            ProductAttribute.value.in_(values),
                        )
                    )
                    for keys, values in requirements
                ),
            )
            .options(
                joinedload(Product.category),
                joinedload(Product.subcategory),
                selectinload(
                    Product.attributes.and_(
                        ProductAttribute.source == ProductAttributeSource.PRIMARY
                    )
                ),
            )
            .order_by(Product.position, Product.id)
            .limit(limit)
        )
        return (await self._session.execute(stmt)).scalars().unique().all()

    async def exists_active(self, product_id: UUID) -> bool:
        stmt = select(Product.id).where(
            Product.id == product_id,
            Product.is_active.is_(True),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def update(self, product: Product) -> Product:
        await self._session.flush()
        return product
