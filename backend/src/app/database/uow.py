from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.modules.activity.gateway import VisitorGateway
from app.api.modules.admin.gateway import DashboardGateway
from app.api.modules.auth.gateway import AuthSessionGateway
from app.api.modules.catalog.gateway import (
    BrandGateway,
    CategoryGateway,
    ProductGateway,
)
from app.api.modules.checkout.gateway import PromotionGateway
from app.api.modules.custom_boards.gateway import CustomBoardGateway
from app.api.modules.customers.gateway import CustomerGateway
from app.api.modules.leads.gateway import LeadGateway
from app.api.modules.orders.gateway import OrderGateway
from app.api.modules.outbox.gateway import OutboxGateway
from app.api.modules.users.gateway import UserGateway


class UnitOfWork:
    dashboard: DashboardGateway
    visitors: VisitorGateway
    auth_sessions: AuthSessionGateway
    users: UserGateway
    brands: BrandGateway
    categories: CategoryGateway
    products: ProductGateway
    promotions: PromotionGateway
    orders: OrderGateway
    leads: LeadGateway
    outbox: OutboxGateway
    custom_boards: CustomBoardGateway
    customers: CustomerGateway

    def __init__(self, session: AsyncSession):
        self.session = session
        self.dashboard = DashboardGateway(session)
        self.visitors = VisitorGateway(session)
        self.auth_sessions = AuthSessionGateway(session)
        self.users = UserGateway(session)
        self.brands = BrandGateway(session)
        self.categories = CategoryGateway(session)
        self.products = ProductGateway(session)
        self.promotions = PromotionGateway(session)
        self.orders = OrderGateway(session)
        self.leads = LeadGateway(session)
        self.outbox = OutboxGateway(session)
        self.custom_boards = CustomBoardGateway(session)
        self.customers = CustomerGateway(session)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def commit(self: Self) -> None:
        await self.session.commit()

    async def rollback(self: Self) -> None:
        await self.session.rollback()
