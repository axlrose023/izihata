from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, Header

from app.api.common.rate_limit import ORDER_RATE_LIMIT, RateLimit
from app.api.modules.orders.schema import CreateOrderRequest, OrderResponse
from app.api.modules.orders.service import OrderCreationService

router = APIRouter(route_class=DishkaRoute)


@router.post(
    "",
    response_model=OrderResponse,
    status_code=201,
    dependencies=[Depends(RateLimit(ORDER_RATE_LIMIT))],
)
async def create_order(
    request: CreateOrderRequest,
    service: FromDishka[OrderCreationService],
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=8,
            max_length=128,
            pattern=r"^[A-Za-z0-9._:-]+$",
        ),
    ],
) -> OrderResponse:
    return await service.create_order(request, idempotency_key)
