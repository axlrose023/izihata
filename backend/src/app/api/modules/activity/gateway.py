from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

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

    @staticmethod
    def _filtered(stmt: Select, params: VisitorListParams) -> Select:
        if params.with_contacts:
            stmt = stmt.where(SiteVisitor.phone.is_not(None))
        if params.search:
            pattern = f"%{params.search}%"
            stmt = stmt.where(
                or_(
                    SiteVisitor.phone.ilike(pattern),
                    SiteVisitor.name.ilike(pattern),
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
