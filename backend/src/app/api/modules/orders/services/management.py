from uuid import UUID

from app.api.common.exceptions import NotFoundError
from app.api.modules.orders.schema import (
    OrderListParams,
    OrderListResponse,
    OrderResponse,
    OrderSummaryResponse,
    UpdateOrderStatusRequest,
)
from app.api.modules.orders.services.status_transition import (
    OrderStatusTransitionService,
)
from app.database.uow import UnitOfWork


class OrderManagementService:
    def __init__(
        self,
        uow: UnitOfWork,
        transitions: OrderStatusTransitionService,
    ):
        self._uow = uow
        self._transitions = transitions

    async def list_orders(self, params: OrderListParams) -> OrderListResponse:
        orders = await self._uow.orders.list(params)
        total = await self._uow.orders.count(params)
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

    async def update_status(
        self,
        order_id: UUID,
        request: UpdateOrderStatusRequest,
    ) -> OrderResponse:
        order = await self._uow.orders.get_by_id_for_update(order_id)
        if order is None:
            raise NotFoundError("Order not found")
        if request.status == order.status:
            return OrderResponse.from_order(order)

        old_status = order.status
        self._transitions.ensure_allowed(old_status, request.status)
        order.status = request.status
        await self._uow.outbox.add(
            topic="order.status_changed",
            payload={
                "order_id": str(order.id),
                "order_number": order.number,
                "old_status": old_status.value,
                "new_status": order.status.value,
            },
        )
        await self._uow.commit()
        return OrderResponse.from_order(order)
