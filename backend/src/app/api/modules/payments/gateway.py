from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.modules.orders.models import Order
from app.api.modules.payments.enums import PaymentAttemptStatus
from app.api.modules.payments.models import PaymentAttempt


class PaymentAttemptGateway:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, attempt: PaymentAttempt) -> PaymentAttempt:
        self._session.add(attempt)
        await self._session.flush()
        return attempt

    async def get_by_order_id(self, order_id: UUID) -> PaymentAttempt | None:
        stmt = (
            select(PaymentAttempt)
            .where(PaymentAttempt.order_id == order_id)
            .order_by(PaymentAttempt.created_at.desc(), PaymentAttempt.id.desc())
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_reference_for_update(
        self, order_reference: str
    ) -> PaymentAttempt | None:
        stmt = (
            select(PaymentAttempt)
            .join(Order, PaymentAttempt.order_id == Order.id)
            .where(PaymentAttempt.order_reference == order_reference)
            .options(selectinload(PaymentAttempt.order))
            .with_for_update(of=Order)
            .execution_options(populate_existing=True)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_id(self, attempt_id: UUID) -> PaymentAttempt | None:
        stmt = (
            select(PaymentAttempt)
            .where(PaymentAttempt.id == attempt_id)
            .options(selectinload(PaymentAttempt.order))
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def has_other_paid_attempt(self, attempt: PaymentAttempt) -> bool:
        stmt = select(
            exists().where(
                PaymentAttempt.order_id == attempt.order_id,
                PaymentAttempt.id != attempt.id,
                PaymentAttempt.status == PaymentAttemptStatus.PAID,
            )
        )
        return bool(await self._session.scalar(stmt))
