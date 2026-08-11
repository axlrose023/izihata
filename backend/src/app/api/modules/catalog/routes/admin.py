from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, status

from app.api.modules.auth.service import AuthenticateUser
from app.api.modules.catalog.schema import (
    CreateProductRequest,
    ProductResponse,
    UpdateProductRequest,
)
from app.api.modules.catalog.service import ProductManagementService
from app.api.modules.users.models import User

router = APIRouter(route_class=DishkaRoute)


@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_product(
    request: CreateProductRequest,
    service: FromDishka[ProductManagementService],
    current_user: User = Depends(AuthenticateUser()),
) -> ProductResponse:
    return await service.create_product(request)


@router.patch("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    request: UpdateProductRequest,
    service: FromDishka[ProductManagementService],
    current_user: User = Depends(AuthenticateUser()),
) -> ProductResponse:
    return await service.update_product(product_id, request)
