from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends

from app.api.modules.auth.service import AuthenticateUser
from app.api.modules.catalog.schema import ProductResponse, UpdateProductRequest
from app.api.modules.catalog.service import ProductManagementService
from app.api.modules.users.models import User

router = APIRouter(route_class=DishkaRoute)


@router.patch("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    request: UpdateProductRequest,
    service: FromDishka[ProductManagementService],
    current_user: User = Depends(AuthenticateUser()),
) -> ProductResponse:
    return await service.update_product(product_id, request)
