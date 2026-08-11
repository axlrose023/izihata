from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, Query

from app.api.modules.auth.service import AuthenticateUser
from app.api.modules.orders.schema import (
    OrderListParams,
    OrderListResponse,
    OrderResponse,
    UpdateOrderStatusRequest,
)
from app.api.modules.orders.service import OrderManagementService
from app.api.modules.users.models import User

router = APIRouter(route_class=DishkaRoute)


@router.get("", response_model=OrderListResponse)
async def get_orders(
    service: FromDishka[OrderManagementService],
    params: Annotated[OrderListParams, Query()],
    current_user: User = Depends(AuthenticateUser()),
) -> OrderListResponse:
    return await service.list_orders(params)


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: UUID,
    request: UpdateOrderStatusRequest,
    service: FromDishka[OrderManagementService],
    current_user: User = Depends(AuthenticateUser()),
) -> OrderResponse:
    return await service.update_status(order_id, request)
