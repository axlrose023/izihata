from collections.abc import Sequence
from urllib.parse import quote
from uuid import UUID
from xml.etree.ElementTree import Element, SubElement, tostring

from app.api.common.exceptions import NotFoundError
from app.api.modules.catalog.enums import ProductRelationKind
from app.api.modules.catalog.models import Product
from app.api.modules.catalog.schema import (
    CatalogSectionResponse,
    CategoryResponse,
    FacetOption,
    PriceFacet,
    ProductDetailResponse,
    ProductFacets,
    ProductListParams,
    ProductListResponse,
    ProductResponse,
    ProductReviewListParams,
    ProductReviewPageResponse,
    ProductReviewResponse,
    SubcategoryResponse,
)
from app.database.uow import UnitOfWork


class CatalogQueryService:
    def __init__(self, uow: UnitOfWork, site_origin: str = "http://localhost:3000"):
        self._uow = uow
        self._site_origin = site_origin.rstrip("/")

    async def get_sitemap(self) -> str:
        namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
        root = Element(f"{{{namespace}}}urlset")
        urls = {"/", "/catalog", "/brands"}
        for section in await self._uow.categories.list_active_sections():
            urls.add(f"/sections/{section.slug}")
        urls.update(
            f"/catalog/{category.slug}"
            for category in await self._uow.categories.list_active()
        )
        urls.update(
            f"/brands/{brand.slug}"
            for brand in await self._uow.brands.list(only_active=True)
        )
        urls.update(
            f"/product/{slug}" for slug in await self._uow.products.list_active_slugs()
        )
        for path in sorted(urls):
            url = SubElement(root, f"{{{namespace}}}url")
            location = SubElement(url, f"{{{namespace}}}loc")
            location.text = f"{self._site_origin}{quote(path, safe='/')}"
        return tostring(root, encoding="unicode", xml_declaration=True)

    async def get_categories(self) -> list[CategoryResponse]:
        categories = await self._uow.categories.list_active()
        (
            category_counts,
            subcategory_counts,
        ) = await self._uow.categories.category_and_subcategory_product_counts()
        return [
            CategoryResponse(
                id=category.id,
                slug=category.slug,
                name=category.name,
                accent=category.accent,
                product_count=category_counts.get(category.id, 0),
                subcategories=[
                    SubcategoryResponse(
                        id=subcategory.id,
                        slug=subcategory.slug,
                        name=subcategory.name,
                        product_count=subcategory_counts.get(subcategory.id, 0),
                    )
                    for subcategory in category.subcategories
                    if subcategory.is_active
                ],
            )
            for category in categories
        ]

    async def get_sections(self) -> list[CatalogSectionResponse]:
        sections = await self._uow.categories.list_active_sections()
        (
            category_counts,
            subcategory_counts,
        ) = await self._uow.categories.category_and_subcategory_product_counts()
        return [
            CatalogSectionResponse.from_section(
                section,
                category_counts,
                subcategory_counts,
            )
            for section in sections
        ]

    async def get_products(self, params: ProductListParams) -> ProductListResponse:
        products = await self._uow.products.list(params)
        total = await self._uow.products.count(params)
        if params.include_facets:
            brand_rows = await self._uow.products.brand_facets(params)
            attribute_rows = await self._uow.products.attribute_facets(params)
            minimum, maximum = await self._uow.products.price_facet(params)
            availability_rows = await self._uow.products.availability_facets(params)
            sale_unit_rows = await self._uow.products.sale_unit_facets(params)
        else:
            brand_rows = []
            attribute_rows = []
            minimum, maximum = None, None
            availability_rows = []
            sale_unit_rows = []

        spec_facets: dict[str, list[FacetOption]] = {}
        for key, value, count in attribute_rows:
            spec_facets.setdefault(key, []).append(
                FacetOption(value=value, count=count)
            )

        total_pages = (total + params.page_size - 1) // params.page_size
        return ProductListResponse(
            items=[ProductResponse.from_product(product) for product in products],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
            has_next=params.page < total_pages,
            has_prev=params.page > 1,
            facets=ProductFacets(
                brands=[
                    FacetOption(value=brand, count=count) for brand, count in brand_rows
                ],
                specs=spec_facets,
                availability=[
                    FacetOption(value=status.value, count=count)
                    for status, count in availability_rows
                ],
                sale_units=[
                    FacetOption(value=value, count=count)
                    for value, count in sale_unit_rows
                ],
                price=PriceFacet(minimum=minimum, maximum=maximum),
            ),
        )

    async def get_product(self, product_slug: str) -> ProductDetailResponse:
        product = await self._uow.products.get_by_slug(product_slug)
        if product is None:
            raise NotFoundError("Product not found")
        reviews = await self._uow.products.list_published_reviews(
            product.id,
            offset=0,
            limit=10,
        )
        related, alternatives, bought_together = await self._get_relations(product.id)
        return ProductDetailResponse.from_product(
            product,
            reviews=list(reviews),
            related=list(related),
            alternatives=list(alternatives),
            bought_together=list(bought_together),
        )

    async def get_product_reviews(
        self,
        product_slug: str,
        params: ProductReviewListParams,
    ) -> ProductReviewPageResponse:
        product = await self._uow.products.get_active_id_and_review_count_by_slug(
            product_slug
        )
        if product is None:
            raise NotFoundError("Product not found")
        product_id, total = product
        reviews = await self._uow.products.list_published_reviews(
            product_id,
            offset=params.offset,
            limit=params.page_size,
        )
        total_pages = (total + params.page_size - 1) // params.page_size
        return ProductReviewPageResponse(
            items=[ProductReviewResponse.from_review(review) for review in reviews],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
            has_next=params.page < total_pages,
            has_prev=params.page > 1,
        )

    async def get_recommendations(
        self,
        product_ids: list[UUID],
    ) -> list[ProductResponse]:
        products = await self._uow.products.list_related_to_any(
            set(product_ids),
            ProductRelationKind.BOUGHT_TOGETHER,
        )
        return [ProductResponse.from_product(product) for product in products]

    async def get_featured_reviews(self) -> list[ProductReviewResponse]:
        reviews = await self._uow.products.list_featured_reviews()
        return [ProductReviewResponse.from_review(review) for review in reviews]

    async def _get_relations(
        self,
        product_id: UUID,
    ) -> tuple[Sequence[Product], Sequence[Product], Sequence[Product]]:
        return (
            await self._uow.products.list_related(
                product_id,
                ProductRelationKind.RELATED,
            ),
            await self._uow.products.list_related(
                product_id,
                ProductRelationKind.ALTERNATIVE,
            ),
            await self._uow.products.list_related(
                product_id,
                ProductRelationKind.BOUGHT_TOGETHER,
            ),
        )
