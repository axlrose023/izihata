from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.common.query import literal_contains
from app.api.modules.activity.models import SiteVisitor
from app.api.modules.activity.schema import VisitorListParams


class VisitorGateway:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_key(self, visitor_key: UUID) -> SiteVisitor | None:
        stmt = select(SiteVisitor).where(SiteVisitor.visitor_key == visitor_key)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def create(self, visitor: SiteVisitor) -> SiteVisitor:
        self._session.add(visitor)
        await self._session.flush()
        return visitor

    async def increment_visit(
        self,
        visitor_key: UUID,
        *,
        now: datetime,
        path: str,
        user_agent: str | None,
        customer_id: UUID | None,
    ) -> None:
        values = {
            "page_views": SiteVisitor.page_views + 1,
            "last_seen_at": now,
            "last_path": path,
        }
        if user_agent:
            values["user_agent"] = user_agent
        if customer_id is not None:
            values["customer_id"] = customer_id
        await self._session.execute(
            update(SiteVisitor)
            .where(SiteVisitor.visitor_key == visitor_key)
            .values(**values)
        )

    async def increment_contact(
        self, visitor_key: UUID, *, name: str | None, phone: str | None, kind: str
    ) -> None:
        values: dict[str, object] = {}
        if name:
            values["name"] = name
        if phone:
            values["phone"] = phone
        if kind == "order":
            values["orders_count"] = SiteVisitor.orders_count + 1
        elif kind == "lead":
            values["leads_count"] = SiteVisitor.leads_count + 1
        if values:
            await self._session.execute(
                update(SiteVisitor)
                .where(SiteVisitor.visitor_key == visitor_key)
                .values(**values)
            )

    @staticmethod
    def _filtered(stmt: Select, params: VisitorListParams) -> Select:
        if params.with_contacts:
            stmt = stmt.where(SiteVisitor.phone.is_not(None))
        if params.search:
            stmt = stmt.where(
                or_(
                    literal_contains(SiteVisitor.phone, params.search),
                    literal_contains(SiteVisitor.name, params.search),
                )
            )
        return stmt

    async def list(self, params: VisitorListParams) -> Sequence[SiteVisitor]:
        stmt = (
            self._filtered(select(SiteVisitor), params)
            .order_by(SiteVisitor.last_seen_at.desc(), SiteVisitor.id)
            .offset((params.page - 1) * params.page_size)
            .limit(params.page_size)
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def count(self, params: VisitorListParams) -> int:
        stmt = self._filtered(select(func.count(SiteVisitor.id)), params)
        return int((await self._session.execute(stmt)).scalar_one())
