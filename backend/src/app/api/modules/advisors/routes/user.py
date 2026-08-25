from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends

from app.api.common.rate_limit import QUOTE_RATE_LIMIT, RateLimit
from app.api.modules.advisors.schema import (
    AutonomyRequest,
    AutonomyResponse,
    BreakerRequest,
    BreakerResponse,
    CableSizeRequest,
    CableSizeResponse,
    LedPowerSupplyRequest,
    LedPowerSupplyResponse,
)
from app.api.modules.advisors.service import ElectricalAdvisorService

router = APIRouter(route_class=DishkaRoute)


@router.post(
    "/cable-size",
    response_model=CableSizeResponse,
    dependencies=[Depends(RateLimit(QUOTE_RATE_LIMIT))],
)
async def calculate_cable_size(
    request: CableSizeRequest,
    service: FromDishka[ElectricalAdvisorService],
) -> CableSizeResponse:
    return await service.calculate_cable(request)


@router.post(
    "/breaker",
    response_model=BreakerResponse,
    dependencies=[Depends(RateLimit(QUOTE_RATE_LIMIT))],
)
async def calculate_breaker(
    request: BreakerRequest,
    service: FromDishka[ElectricalAdvisorService],
) -> BreakerResponse:
    return await service.calculate_breaker(request)


@router.post(
    "/led-power-supply",
    response_model=LedPowerSupplyResponse,
    dependencies=[Depends(RateLimit(QUOTE_RATE_LIMIT))],
)
async def calculate_led_power_supply(
    request: LedPowerSupplyRequest,
    service: FromDishka[ElectricalAdvisorService],
) -> LedPowerSupplyResponse:
    return await service.calculate_led_power_supply(request)


@router.post(
    "/autonomy",
    response_model=AutonomyResponse,
    dependencies=[Depends(RateLimit(QUOTE_RATE_LIMIT))],
)
async def calculate_autonomy(
    request: AutonomyRequest,
    service: FromDishka[ElectricalAdvisorService],
) -> AutonomyResponse:
    return await service.calculate_autonomy(request)
