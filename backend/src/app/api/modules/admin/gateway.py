from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.modules.catalog.models import Product
from app.api.modules.leads.enums import LeadStatus
from app.api.modules.leads.models import Lead
from app.api.modules.orders.enums import OrderStatus
from app.api.modules.orders.models import Order


@dataclass(frozen=True, slots=True)
class DashboardStats:
    revenue_last_7_days: Decimal
    orders_today: int
    average_order_total: Decimal
    active_products: int
    new_leads: int


class DashboardGateway:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_stats(
        self,
        today: datetime,
        week_ago: datetime,
    ) -> DashboardStats:
        revenue = (
            select(func.coalesce(func.sum(Order.total), 0))
            .where(
                Order.created_at >= week_ago,
                Order.status != OrderStatus.CANCELLED,
            )
            .scalar_subquery()
        )
        orders_today = (
            select(func.count(Order.id))
            .where(Order.created_at >= today)
            .scalar_subquery()
        )
        average_total = (
            select(func.coalesce(func.avg(Order.total), 0))
            .where(Order.status != OrderStatus.CANCELLED)
            .scalar_subquery()
        )
        active_products = (
            select(func.count(Product.id))
            .where(Product.is_active.is_(True))
            .scalar_subquery()
        )
        new_leads = (
            select(func.count(Lead.id))
            .where(Lead.status == LeadStatus.NEW)
            .scalar_subquery()
        )
        row = (
            await self._session.execute(
                select(
                    revenue.label("revenue_last_7_days"),
                    orders_today.label("orders_today"),
                    average_total.label("average_order_total"),
                    active_products.label("active_products"),
                    new_leads.label("new_leads"),
                )
            )
        ).one()
        return DashboardStats(
            revenue_last_7_days=Decimal(row.revenue_last_7_days),
            orders_today=int(row.orders_today),
            average_order_total=Decimal(row.average_order_total),
            active_products=int(row.active_products),
            new_leads=int(row.new_leads),
        )
