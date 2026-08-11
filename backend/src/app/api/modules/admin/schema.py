from decimal import Decimal

from app.api.common.schema import StrictSchema


class DashboardResponse(StrictSchema):
    revenue_last_7_days: Decimal
    orders_today: int
    average_order_total: Decimal
    active_products: int
    new_leads: int
