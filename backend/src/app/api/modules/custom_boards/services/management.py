from uuid import UUID

from app.api.common.exceptions import NotFoundError
from app.api.modules.custom_boards.models import (
    CustomBoardPortfolioItem,
    CustomBoardRequest,
)
from app.api.modules.custom_boards.schema import (
    AdminCustomBoardRequestResponse,
    CreatePortfolioItemRequest,
    CustomBoardRequestListParams,
    CustomBoardRequestListResponse,
    PortfolioItemResponse,
    UpdateCustomBoardRequestStatus,
    UpdatePortfolioItemRequest,
)
from app.api.modules.custom_boards.services.status_transition import (
    BoardStatusTransitionService,
)
from app.database.uow import UnitOfWork


class CustomBoardManagementService:
    def __init__(
        self,
        uow: UnitOfWork,
        transitions: BoardStatusTransitionService,
    ):
        self._uow = uow
        self._transitions = transitions

    async def list_requests(
        self,
        params: CustomBoardRequestListParams,
    ) -> CustomBoardRequestListResponse:
        requests = await self._uow.custom_boards.list_requests(
            offset=params.offset,
            limit=params.page_size,
            status=params.status,
        )
        total = await self._uow.custom_boards.count_requests(params.status)
        total_pages = (total + params.page_size - 1) // params.page_size
        return CustomBoardRequestListResponse(
            items=[self._request_response(request) for request in requests],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
            has_next=params.page < total_pages,
            has_prev=params.page > 1,
        )

    async def update_request_status(
        self,
        request_id: UUID,
        request: UpdateCustomBoardRequestStatus,
    ) -> None:
        board_request = await self._uow.custom_boards.get_request_for_update(request_id)
        if board_request is None:
            raise NotFoundError(
                "Custom board request not found",
                code="custom_board_request_not_found",
            )
        self._transitions.ensure_allowed(board_request.status, request.status)
        board_request.status = request.status
        await self._uow.commit()

    async def create_portfolio_item(
        self,
        request: CreatePortfolioItemRequest,
    ) -> PortfolioItemResponse:
        item = CustomBoardPortfolioItem(**request.model_dump())
        await self._uow.custom_boards.create_portfolio_item(item)
        await self._uow.commit()
        return PortfolioItemResponse.from_item(item)

    async def update_portfolio_item(
        self,
        item_id: UUID,
        request: UpdatePortfolioItemRequest,
    ) -> PortfolioItemResponse:
        item = await self._uow.custom_boards.get_portfolio_item_for_update(item_id)
        if item is None:
            raise NotFoundError(
                "Custom board portfolio item not found",
                code="custom_board_portfolio_item_not_found",
            )
        for field, value in request.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        await self._uow.commit()
        return PortfolioItemResponse.from_item(item)

    @staticmethod
    def _request_response(
        request: CustomBoardRequest,
    ) -> AdminCustomBoardRequestResponse:
        return AdminCustomBoardRequestResponse.from_request(request)
