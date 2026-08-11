from app.api.common.exceptions import NotFoundError
from app.api.modules.catalog.schema import (
    CategoryResponse,
    FacetOption,
    PriceFacet,
    ProductDetailResponse,
    ProductFacets,
    ProductListParams,
    ProductListResponse,
    ProductResponse,
    ProductReviewResponse,
    SubcategoryResponse,
)
from app.database.uow import UnitOfWork


class CatalogQueryService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def get_categories(self) -> list[CategoryResponse]:
        categories = await self._uow.categories.list_active()
        category_counts = await self._uow.categories.product_counts()
        subcategory_counts = await self._uow.categories.subcategory_product_counts()
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

    async def get_products(self, params: ProductListParams) -> ProductListResponse:
        products = await self._uow.products.list(params)
        total = await self._uow.products.count(params)
        brand_rows = await self._uow.products.brand_facets(params)
        attribute_rows = await self._uow.products.attribute_facets(params)
        minimum, maximum = await self._uow.products.price_facet(params)

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
                price=PriceFacet(minimum=minimum, maximum=maximum),
            ),
        )

    async def get_product(self, product_slug: str) -> ProductDetailResponse:
        product = await self._uow.products.get_by_slug(product_slug)
        if product is None:
            raise NotFoundError("Product not found")
        return ProductDetailResponse.from_product(product)

    async def get_featured_reviews(self) -> list[ProductReviewResponse]:
        reviews = await self._uow.products.list_featured_reviews()
        return [ProductReviewResponse.from_review(review) for review in reviews]
