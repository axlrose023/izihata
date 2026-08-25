from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.api.modules.orders.models import Order
from app.api.modules.orders.schema import OrderListParams


class OrderGateway:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, order: Order) -> Order:
        self._session.add(order)
        await self._session.flush()
        return order

    async def get_by_idempotency_key(self, key: str) -> Order | None:
        stmt = (
            select(Order)
            .where(Order.idempotency_key == key)
            .options(selectinload(Order.items))
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_id_for_update(self, order_id: UUID) -> Order | None:
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items))
            .with_for_update()
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    def _conditions(self, params: OrderListParams) -> list[ColumnElement[bool]]:
        return [Order.status == params.status] if params.status else []

    async def list(self, params: OrderListParams) -> Sequence[Order]:
        stmt = (
            select(Order)
            .where(*self._conditions(params))
            .order_by(Order.created_at.desc(), Order.id.desc())
            .offset(params.offset)
            .limit(params.page_size)
        )
        return (await self._session.execute(stmt)).scalars().unique().all()

    async def count(self, params: OrderListParams) -> int:
        stmt = select(func.count(Order.id)).where(*self._conditions(params))
        return int((await self._session.execute(stmt)).scalar_one())

    async def list_for_customer(
        self,
        customer_id: UUID,
        params: OrderListParams,
    ) -> Sequence[Order]:
        stmt = (
            select(Order)
            .where(Order.customer_id == customer_id, *self._conditions(params))
            .order_by(Order.created_at.desc(), Order.id.desc())
            .offset(params.offset)
            .limit(params.page_size)
        )
        return (await self._session.execute(stmt)).scalars().unique().all()

    async def count_for_customer(
        self, customer_id: UUID, params: OrderListParams
    ) -> int:
        stmt = select(func.count(Order.id)).where(
            Order.customer_id == customer_id,
            *self._conditions(params),
        )
        return int((await self._session.execute(stmt)).scalar_one())
