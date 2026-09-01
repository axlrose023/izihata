from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, Header, Request

from app.api.common.rate_limit import ORDER_RATE_LIMIT, RateLimit
from app.api.common.visitor import visitor_key_from
from app.api.modules.activity.service import VisitorTrackingService
from app.api.modules.customers.models import Customer
from app.api.modules.customers.service import OptionalAuthenticateCustomer
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
    http_request: Request,
    service: FromDishka[OrderCreationService],
    tracking: FromDishka[VisitorTrackingService],
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=8,
            max_length=128,
            pattern=r"^[A-Za-z0-9._:-]+$",
        ),
    ],
    customer: Customer | None = Depends(OptionalAuthenticateCustomer()),
) -> OrderResponse:
    order = await service.create_order(
        request,
        idempotency_key,
        customer_id=customer.id if customer is not None else None,
    )
    await tracking.record_contact(
        visitor_key_from(http_request),
        name=request.customer_name,
        phone=request.phone,
        kind="order",
    )
    return order
