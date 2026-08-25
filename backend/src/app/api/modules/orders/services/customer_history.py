from app.api.modules.customers.models import Customer
from app.api.modules.orders.schema import (
    OrderListParams,
    OrderListResponse,
    OrderSummaryResponse,
)
from app.database.uow import UnitOfWork


class CustomerOrderHistoryService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def list_orders(
        self,
        customer: Customer,
        params: OrderListParams,
    ) -> OrderListResponse:
        orders = await self._uow.orders.list_for_customer(customer.id, params)
        total = await self._uow.orders.count_for_customer(customer.id, params)
        total_pages = (total + params.page_size - 1) // params.page_size
        return OrderListResponse(
            items=[OrderSummaryResponse.from_order(order) for order in orders],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
            has_next=params.page < total_pages,
            has_prev=params.page > 1,
        )
