from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends

from app.api.common.rate_limit import QUOTE_RATE_LIMIT, RateLimit
from app.api.modules.checkout.schema import QuoteRequest, QuoteResponse
from app.api.modules.checkout.service import PricingService

router = APIRouter(route_class=DishkaRoute)


@router.post(
    "/quote",
    response_model=QuoteResponse,
    dependencies=[Depends(RateLimit(QUOTE_RATE_LIMIT))],
)
async def create_quote(
    request: QuoteRequest,
    service: FromDishka[PricingService],
) -> QuoteResponse:
    return await service.quote(request)
