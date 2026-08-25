from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, Query, status

from app.api.modules.auth.service import AuthenticateUser
from app.api.modules.custom_boards.schema import (
    CreatePortfolioItemRequest,
    CustomBoardRequestListParams,
    CustomBoardRequestListResponse,
    PortfolioItemResponse,
    UpdateCustomBoardRequestStatus,
    UpdatePortfolioItemRequest,
)
from app.api.modules.custom_boards.service import CustomBoardManagementService
from app.api.modules.users.models import User

router = APIRouter(route_class=DishkaRoute)


@router.get("/requests", response_model=CustomBoardRequestListResponse)
async def get_requests(
    service: FromDishka[CustomBoardManagementService],
    params: Annotated[CustomBoardRequestListParams, Query()],
    current_user: User = Depends(AuthenticateUser()),
) -> CustomBoardRequestListResponse:
    return await service.list_requests(params)


@router.patch("/requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_request_status(
    request_id: UUID,
    request: UpdateCustomBoardRequestStatus,
    service: FromDishka[CustomBoardManagementService],
    current_user: User = Depends(AuthenticateUser()),
) -> None:
    await service.update_request_status(request_id, request)


@router.post(
    "/portfolio",
    response_model=PortfolioItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_portfolio_item(
    request: CreatePortfolioItemRequest,
    service: FromDishka[CustomBoardManagementService],
    current_user: User = Depends(AuthenticateUser()),
) -> PortfolioItemResponse:
    return await service.create_portfolio_item(request)


@router.patch("/portfolio/{item_id}", response_model=PortfolioItemResponse)
async def update_portfolio_item(
    item_id: UUID,
    request: UpdatePortfolioItemRequest,
    service: FromDishka[CustomBoardManagementService],
    current_user: User = Depends(AuthenticateUser()),
) -> PortfolioItemResponse:
    return await service.update_portfolio_item(item_id, request)
