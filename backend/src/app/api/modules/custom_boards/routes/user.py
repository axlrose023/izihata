from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, status

from app.api.common.rate_limit import LEAD_RATE_LIMIT, QUOTE_RATE_LIMIT, RateLimit
from app.api.modules.custom_boards.schema import (
    BoardEstimateRequest,
    BoardEstimateResponse,
    CreateCustomBoardRequest,
    CustomBoardRequestResponse,
    PortfolioItemResponse,
)
from app.api.modules.custom_boards.service import (
    BoardEstimationService,
    CustomBoardCreationService,
    CustomBoardPublicQueryService,
)

router = APIRouter(route_class=DishkaRoute)


@router.get("/portfolio", response_model=list[PortfolioItemResponse])
async def get_portfolio(
    service: FromDishka[CustomBoardPublicQueryService],
) -> list[PortfolioItemResponse]:
    return await service.list_portfolio()


@router.post(
    "/estimate",
    response_model=BoardEstimateResponse,
    dependencies=[Depends(RateLimit(QUOTE_RATE_LIMIT))],
)
async def estimate_board(
    request: BoardEstimateRequest,
    service: FromDishka[BoardEstimationService],
) -> BoardEstimateResponse:
    return service.estimate(request)


@router.post(
    "/requests",
    response_model=CustomBoardRequestResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimit(LEAD_RATE_LIMIT))],
)
async def create_request(
    request: CreateCustomBoardRequest,
    service: FromDishka[CustomBoardCreationService],
) -> CustomBoardRequestResponse:
    return await service.create(request)
