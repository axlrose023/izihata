from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from app.api.modules.activity.models import SiteVisitor
from app.api.modules.activity.schema import TrackVisitRequest
from app.database.uow import UnitOfWork


class VisitorTrackingService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def track(
        self,
        visitor_key: UUID | None,
        request: TrackVisitRequest,
        *,
        user_agent: str | None,
        customer_id: UUID | None,
    ) -> UUID:
        """Record one page view and return the key to store in the cookie."""
        key = visitor_key or uuid4()
        now = datetime.now(UTC)
        visitor = await self._uow.visitors.get_by_key(key)
        if visitor is None:
            visitor = SiteVisitor(
                visitor_key=key,
                first_seen_at=now,
                last_seen_at=now,
                page_views=1,
                last_path=request.path,
                user_agent=user_agent,
                customer_id=customer_id,
            )
            try:
                await self._uow.visitors.create(visitor)
                await self._uow.commit()
            except IntegrityError:
                # A parallel first request already claimed this key.
                await self._uow.rollback()
                return key
            return key

        visitor.last_seen_at = now
        visitor.page_views += 1
        visitor.last_path = request.path
        if user_agent:
            visitor.user_agent = user_agent
        if customer_id is not None:
            visitor.customer_id = customer_id
        await self._uow.commit()
        return key

    async def record_contact(
        self,
        visitor_key: UUID | None,
        *,
        name: str | None,
        phone: str | None,
        kind: str,
    ) -> None:
        """Attach the details a visitor left in a lead or an order.

        Called after the lead or order is committed, so a failure here can
        never roll back the thing the customer actually asked for.
        """
        if visitor_key is None:
            return
        visitor = await self._uow.visitors.get_by_key(visitor_key)
        if visitor is None:
            return
        if name:
            visitor.name = name
        if phone:
            visitor.phone = phone
        if kind == "order":
            visitor.orders_count += 1
        elif kind == "lead":
            visitor.leads_count += 1
        await self._uow.commit()
