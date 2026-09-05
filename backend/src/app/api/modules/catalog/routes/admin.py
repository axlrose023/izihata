from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.api.modules.auth.service import AuthenticateUser
from app.api.modules.catalog.schema import (
    AdminBrandResponse,
    AdminCatalogSectionResponse,
    AdminProductDetailResponse,
    AdminProductResponse,
    CatalogAttributeResponse,
    CategoryAttributeResponse,
    CreateCatalogAttributeRequest,
    CreateCatalogSectionRequest,
    CreateProductRequest,
    ProductReviewListParams,
    ProductReviewListResponse,
    ReplaceCategoryAttributesRequest,
    ReviewModerationRequest,
    UpdateBrandRequest,
    UpdateCatalogSectionRequest,
    UpdateCategorySectionRequest,
    UpdateProductRequest,
)
from app.api.modules.catalog.service import (
    BrandManagementService,
    CatalogAdministrationService,
    ProductManagementService,
)
from app.api.modules.catalog.services.media import MediaStorageService
from app.api.modules.users.models import User

router = APIRouter(route_class=DishkaRoute)


@router.post(
    "/products",
    response_model=AdminProductResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_product(
    request: CreateProductRequest,
    service: FromDishka[ProductManagementService],
    current_user: User = Depends(AuthenticateUser()),
) -> AdminProductResponse:
    return await service.create_product(request)


@router.get("/products/{product_id}", response_model=AdminProductDetailResponse)
async def get_product(
    product_id: UUID,
    service: FromDishka[ProductManagementService],
    current_user: User = Depends(AuthenticateUser()),
) -> AdminProductDetailResponse:
    return await service.get_product(product_id)


@router.patch("/products/{product_id}", response_model=AdminProductResponse)
async def update_product(
    product_id: UUID,
    request: UpdateProductRequest,
    service: FromDishka[ProductManagementService],
    current_user: User = Depends(AuthenticateUser()),
) -> AdminProductResponse:
    return await service.update_product(product_id, request)


@router.post(
    "/sections",
    response_model=AdminCatalogSectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_section(
    request: CreateCatalogSectionRequest,
    service: FromDishka[CatalogAdministrationService],
    current_user: User = Depends(AuthenticateUser()),
) -> AdminCatalogSectionResponse:
    return await service.create_section(request)


@router.patch("/sections/{section_id}", response_model=AdminCatalogSectionResponse)
async def update_section(
    section_id: UUID,
    request: UpdateCatalogSectionRequest,
    service: FromDishka[CatalogAdministrationService],
    current_user: User = Depends(AuthenticateUser()),
) -> AdminCatalogSectionResponse:
    return await service.update_section(section_id, request)


@router.patch(
    "/categories/{category_id}/section", status_code=status.HTTP_204_NO_CONTENT
)
async def assign_category_section(
    category_id: UUID,
    request: UpdateCategorySectionRequest,
    service: FromDishka[CatalogAdministrationService],
    current_user: User = Depends(AuthenticateUser()),
) -> None:
    await service.assign_category_section(category_id, request)


@router.post("/media", status_code=status.HTTP_201_CREATED)
async def upload_media(
    service: FromDishka[MediaStorageService],
    file: UploadFile = File(),
    current_user: User = Depends(AuthenticateUser()),
) -> dict[str, str]:
    return {"url": await service.store(file)}


@router.get("/brands", response_model=list[AdminBrandResponse])
async def get_brands(
    service: FromDishka[BrandManagementService],
    current_user: User = Depends(AuthenticateUser()),
) -> list[AdminBrandResponse]:
    return await service.list_brands()


@router.patch("/brands/{brand_id}", response_model=AdminBrandResponse)
async def update_brand(
    brand_id: UUID,
    request: UpdateBrandRequest,
    service: FromDishka[BrandManagementService],
    current_user: User = Depends(AuthenticateUser()),
) -> AdminBrandResponse:
    return await service.update_brand(brand_id, request)


@router.get("/attributes", response_model=list[CatalogAttributeResponse])
async def get_attributes(
    service: FromDishka[CatalogAdministrationService],
    current_user: User = Depends(AuthenticateUser()),
) -> list[CatalogAttributeResponse]:
    return await service.list_attributes()


@router.post(
    "/attributes",
    response_model=CatalogAttributeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_attribute(
    request: CreateCatalogAttributeRequest,
    service: FromDishka[CatalogAdministrationService],
    current_user: User = Depends(AuthenticateUser()),
) -> CatalogAttributeResponse:
    return await service.create_attribute(request)


@router.get(
    "/categories/{category_id}/attributes",
    response_model=list[CategoryAttributeResponse],
)
async def get_category_attributes(
    category_id: UUID,
    service: FromDishka[CatalogAdministrationService],
    current_user: User = Depends(AuthenticateUser()),
) -> list[CategoryAttributeResponse]:
    return await service.list_category_attributes(category_id)


@router.put(
    "/categories/{category_id}/attributes",
    response_model=list[CategoryAttributeResponse],
)
async def replace_category_attributes(
    category_id: UUID,
    request: ReplaceCategoryAttributesRequest,
    service: FromDishka[CatalogAdministrationService],
    current_user: User = Depends(AuthenticateUser()),
) -> list[CategoryAttributeResponse]:
    return await service.replace_category_attributes(category_id, request)


@router.get("/reviews", response_model=ProductReviewListResponse)
async def get_reviews(
    service: FromDishka[CatalogAdministrationService],
    params: Annotated[ProductReviewListParams, Query()],
    current_user: User = Depends(AuthenticateUser()),
) -> ProductReviewListResponse:
    return await service.list_reviews(params)


@router.patch("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def moderate_review(
    review_id: UUID,
    request: ReviewModerationRequest,
    service: FromDishka[CatalogAdministrationService],
    current_user: User = Depends(AuthenticateUser()),
) -> None:
    await service.moderate_review(review_id, request)
