from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.api.modules.leads.models import Lead
from app.api.modules.leads.schema import LeadListParams


class LeadGateway:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, lead: Lead) -> Lead:
        self._session.add(lead)
        await self._session.flush()
        return lead

    def _conditions(self, params: LeadListParams) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = []
        if params.status is not None:
            conditions.append(Lead.status == params.status)
        if params.type is not None:
            conditions.append(Lead.type == params.type)
        return conditions

    async def list(self, params: LeadListParams) -> Sequence[Lead]:
        stmt = (
            select(Lead)
            .where(*self._conditions(params))
            .order_by(Lead.created_at.desc(), Lead.id.desc())
            .offset(params.offset)
            .limit(params.page_size)
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def count(self, params: LeadListParams) -> int:
        stmt = select(func.count(Lead.id)).where(*self._conditions(params))
        return int((await self._session.execute(stmt)).scalar_one())

    async def get_by_id_for_update(self, lead_id: UUID) -> Lead | None:
        stmt = select(Lead).where(Lead.id == lead_id).with_for_update()
        return (await self._session.execute(stmt)).scalar_one_or_none()
