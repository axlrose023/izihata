import pytest

from app.api.common.exceptions import UnprocessableError
from app.api.modules.leads.enums import LeadStatus
from app.api.modules.leads.service import LeadStatusTransitionService
from app.api.modules.orders.enums import OrderStatus
from app.api.modules.orders.service import OrderStatusTransitionService


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (OrderStatus.NEW, OrderStatus.PROCESSING),
        (OrderStatus.NEW, OrderStatus.CANCELLED),
        (OrderStatus.PROCESSING, OrderStatus.CONFIRMED),
        (OrderStatus.PROCESSING, OrderStatus.CANCELLED),
        (OrderStatus.CONFIRMED, OrderStatus.SHIPPED),
        (OrderStatus.CONFIRMED, OrderStatus.CANCELLED),
        (OrderStatus.SHIPPED, OrderStatus.DELIVERED),
    ],
)
def test_all_allowed_order_transitions(current: OrderStatus, target: OrderStatus):
    OrderStatusTransitionService().ensure_allowed(current, target)


@pytest.mark.parametrize("terminal", [OrderStatus.DELIVERED, OrderStatus.CANCELLED])
def test_order_terminal_states_cannot_transition(terminal: OrderStatus):
    with pytest.raises(UnprocessableError):
        OrderStatusTransitionService().ensure_allowed(terminal, OrderStatus.NEW)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (LeadStatus.NEW, LeadStatus.CONTACTED),
        (LeadStatus.NEW, LeadStatus.CLOSED),
        (LeadStatus.CONTACTED, LeadStatus.CLOSED),
    ],
)
def test_all_allowed_lead_transitions(current: LeadStatus, target: LeadStatus):
    LeadStatusTransitionService().ensure_allowed(current, target)


def test_closed_lead_cannot_transition():
    with pytest.raises(UnprocessableError):
        LeadStatusTransitionService().ensure_allowed(
            LeadStatus.CLOSED,
            LeadStatus.CONTACTED,
        )
