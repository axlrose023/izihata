from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, Path, Query

from app.api.common.rate_limit import LEAD_RATE_LIMIT, RateLimit
from app.api.modules.catalog.schema import (
    BrandResponse,
    CatalogSectionResponse,
    CategoryResponse,
    CreateProductReviewRequest,
    CreateProductReviewResponse,
    CreateStockSubscriptionRequest,
    ProductDetailResponse,
    ProductListParams,
    ProductListResponse,
    ProductResponse,
    ProductReviewResponse,
    StockSubscriptionResponse,
)
from app.api.modules.catalog.service import (
    BrandQueryService,
    CatalogQueryService,
    ReviewSubmissionService,
    StockSubscriptionService,
)

router = APIRouter(route_class=DishkaRoute)


@router.get("/categories", response_model=list[CategoryResponse])
async def get_categories(
    service: FromDishka[CatalogQueryService],
) -> list[CategoryResponse]:
    return await service.get_categories()


@router.get("/sections", response_model=list[CatalogSectionResponse])
async def get_sections(
    service: FromDishka[CatalogQueryService],
) -> list[CatalogSectionResponse]:
    return await service.get_sections()


@router.get("/products", response_model=ProductListResponse)
async def get_products(
    service: FromDishka[CatalogQueryService],
    params: Annotated[ProductListParams, Query()],
) -> ProductListResponse:
    return await service.get_products(params)


@router.get("/brands", response_model=list[BrandResponse])
async def get_brands(
    service: FromDishka[BrandQueryService],
) -> list[BrandResponse]:
    return await service.list_brands()


@router.get("/brands/{brand_slug}", response_model=BrandResponse)
async def get_brand(
    brand_slug: Annotated[
        str,
        Path(min_length=1, max_length=96, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"),
    ],
    service: FromDishka[BrandQueryService],
) -> BrandResponse:
    return await service.get_brand(brand_slug)


@router.get("/recommendations", response_model=list[ProductResponse])
async def get_recommendations(
    service: FromDishka[CatalogQueryService],
    product_id: Annotated[list[UUID], Query(alias="id", max_length=50)],
) -> list[ProductResponse]:
    return await service.get_recommendations(product_id)


@router.get("/reviews/featured", response_model=list[ProductReviewResponse])
async def get_featured_reviews(
    service: FromDishka[CatalogQueryService],
) -> list[ProductReviewResponse]:
    return await service.get_featured_reviews()


@router.get("/products/{product_slug}", response_model=ProductDetailResponse)
async def get_product(
    product_slug: Annotated[
        str,
        Path(min_length=1, max_length=180, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"),
    ],
    service: FromDishka[CatalogQueryService],
) -> ProductDetailResponse:
    return await service.get_product(product_slug)


@router.post(
    "/products/{product_slug}/reviews",
    response_model=CreateProductReviewResponse,
    status_code=201,
    dependencies=[Depends(RateLimit(LEAD_RATE_LIMIT))],
)
async def create_product_review(
    product_slug: Annotated[
        str,
        Path(min_length=1, max_length=180, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"),
    ],
    request: CreateProductReviewRequest,
    service: FromDishka[ReviewSubmissionService],
) -> CreateProductReviewResponse:
    return await service.submit(product_slug, request)


@router.post(
    "/products/{product_slug}/stock-subscriptions",
    response_model=StockSubscriptionResponse,
    status_code=201,
    dependencies=[Depends(RateLimit(LEAD_RATE_LIMIT))],
)
async def create_stock_subscription(
    product_slug: Annotated[
        str,
        Path(min_length=1, max_length=180, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"),
    ],
    request: CreateStockSubscriptionRequest,
    service: FromDishka[StockSubscriptionService],
) -> StockSubscriptionResponse:
    return await service.subscribe(product_slug, request)
