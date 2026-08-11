from app.api.common.exceptions import UnprocessableError
from app.api.modules.orders.enums import OrderStatus

STATUS_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.NEW: {OrderStatus.PROCESSING, OrderStatus.CANCELLED},
    OrderStatus.PROCESSING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}


class OrderStatusTransitionService:
    def ensure_allowed(self, current: OrderStatus, target: OrderStatus) -> None:
        if target not in STATUS_TRANSITIONS[current]:
            raise UnprocessableError(
                f"Order cannot move from {current.value} to {target.value}"
            )
