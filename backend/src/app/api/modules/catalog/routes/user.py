from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Path, Query

from app.api.modules.catalog.schema import (
    CategoryResponse,
    ProductDetailResponse,
    ProductListParams,
    ProductListResponse,
    ProductReviewResponse,
)
from app.api.modules.catalog.service import CatalogQueryService

router = APIRouter(route_class=DishkaRoute)


@router.get("/categories", response_model=list[CategoryResponse])
async def get_categories(
    service: FromDishka[CatalogQueryService],
) -> list[CategoryResponse]:
    return await service.get_categories()


@router.get("/products", response_model=ProductListResponse)
async def get_products(
    service: FromDishka[CatalogQueryService],
    params: Annotated[ProductListParams, Query()],
) -> ProductListResponse:
    return await service.get_products(params)


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
