from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, Query, status

from app.api.modules.customers.models import Customer
from app.api.modules.customers.schema import (
    CustomerCompanyRequest,
    CustomerCompanyResponse,
    CustomerProfileResponse,
)
from app.api.modules.customers.service import (
    AuthenticateCustomer,
    CustomerProfileService,
)
from app.api.modules.orders.schema import OrderListParams, OrderListResponse
from app.api.modules.orders.service import CustomerOrderHistoryService

router = APIRouter(route_class=DishkaRoute)


@router.get("/me", response_model=CustomerProfileResponse)
async def get_profile(
    service: FromDishka[CustomerProfileService],
    customer: Customer = Depends(AuthenticateCustomer()),
) -> CustomerProfileResponse:
    return await service.get_profile(customer)


@router.post(
    "/company",
    response_model=CustomerCompanyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_company(
    request: CustomerCompanyRequest,
    service: FromDishka[CustomerProfileService],
    customer: Customer = Depends(AuthenticateCustomer()),
) -> CustomerCompanyResponse:
    return await service.register_company(customer, request)


@router.get("/orders", response_model=OrderListResponse)
async def get_order_history(
    service: FromDishka[CustomerOrderHistoryService],
    params: Annotated[OrderListParams, Query()],
    customer: Customer = Depends(AuthenticateCustomer()),
) -> OrderListResponse:
    return await service.list_orders(customer, params)
