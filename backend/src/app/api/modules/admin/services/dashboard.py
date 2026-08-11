from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.api.modules.admin.schema import DashboardResponse
from app.api.modules.checkout.utils import round_money
from app.database.uow import UnitOfWork
from app.settings import Config


class DashboardService:
    def __init__(self, uow: UnitOfWork, config: Config):
        self._uow = uow
        self._timezone = ZoneInfo(config.business_timezone)

    async def get_dashboard(self) -> DashboardResponse:
        now = datetime.now(self._timezone)
        today = datetime.combine(now.date(), time.min, tzinfo=self._timezone)
        week_ago = (now - timedelta(days=7)).astimezone(UTC)
        stats = await self._uow.dashboard.get_stats(
            today=today.astimezone(UTC),
            week_ago=week_ago,
        )
        return DashboardResponse(
            revenue_last_7_days=round_money(stats.revenue_last_7_days),
            orders_today=stats.orders_today,
            average_order_total=round_money(stats.average_order_total),
            active_products=stats.active_products,
            new_leads=stats.new_leads,
        )
