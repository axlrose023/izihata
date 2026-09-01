from app.api.modules.activity.schema import (
    VisitorListParams,
    VisitorListResponse,
    VisitorResponse,
)
from app.database.uow import UnitOfWork


class VisitorQueryService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def list_visitors(self, params: VisitorListParams) -> VisitorListResponse:
        visitors = await self._uow.visitors.list(params)
        total = await self._uow.visitors.count(params)
        total_pages = (total + params.page_size - 1) // params.page_size
        return VisitorListResponse(
            items=[VisitorResponse.from_visitor(visitor) for visitor in visitors],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
            has_next=params.page < total_pages,
            has_prev=params.page > 1,
        )
