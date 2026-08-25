from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.modules.custom_boards.enums import BoardRequestStatus
from app.api.modules.custom_boards.models import (
    CustomBoardPortfolioItem,
    CustomBoardRequest,
)


class CustomBoardGateway:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_request(self, request: CustomBoardRequest) -> CustomBoardRequest:
        self._session.add(request)
        await self._session.flush()
        return request

    async def list_portfolio(self) -> Sequence[CustomBoardPortfolioItem]:
        stmt = (
            select(CustomBoardPortfolioItem)
            .where(CustomBoardPortfolioItem.is_active.is_(True))
            .order_by(CustomBoardPortfolioItem.position, CustomBoardPortfolioItem.id)
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def create_portfolio_item(
        self,
        item: CustomBoardPortfolioItem,
    ) -> CustomBoardPortfolioItem:
        self._session.add(item)
        await self._session.flush()
        return item

    async def get_portfolio_item_for_update(
        self,
        item_id: UUID,
    ) -> CustomBoardPortfolioItem | None:
        stmt = (
            select(CustomBoardPortfolioItem)
            .where(CustomBoardPortfolioItem.id == item_id)
            .with_for_update()
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_requests(
        self,
        *,
        offset: int,
        limit: int,
        status: BoardRequestStatus | None,
    ) -> Sequence[CustomBoardRequest]:
        stmt = select(CustomBoardRequest)
        if status is not None:
            stmt = stmt.where(CustomBoardRequest.status == status)
        stmt = (
            stmt.order_by(CustomBoardRequest.created_at.desc(), CustomBoardRequest.id)
            .offset(offset)
            .limit(limit)
        )
        return (await self._session.execute(stmt)).scalars().all()

    async def count_requests(self, status: BoardRequestStatus | None) -> int:
        stmt = select(func.count(CustomBoardRequest.id))
        if status is not None:
            stmt = stmt.where(CustomBoardRequest.status == status)
        return int((await self._session.execute(stmt)).scalar_one())

    async def get_request_for_update(
        self,
        request_id: UUID,
    ) -> CustomBoardRequest | None:
        stmt = (
            select(CustomBoardRequest)
            .where(CustomBoardRequest.id == request_id)
            .with_for_update()
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()
