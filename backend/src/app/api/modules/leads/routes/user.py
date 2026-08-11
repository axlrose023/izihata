from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends

from app.api.common.rate_limit import LEAD_RATE_LIMIT, RateLimit
from app.api.modules.leads.schema import CreateLeadRequest, LeadResponse
from app.api.modules.leads.service import LeadCreationService

router = APIRouter(route_class=DishkaRoute)


@router.post(
    "",
    response_model=LeadResponse,
    status_code=201,
    dependencies=[Depends(RateLimit(LEAD_RATE_LIMIT))],
)
async def create_lead(
    request: CreateLeadRequest,
    service: FromDishka[LeadCreationService],
) -> LeadResponse:
    return await service.create(request)
