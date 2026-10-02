import logging

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, Request

from app.api.common.rate_limit import LEAD_RATE_LIMIT, RateLimit
from app.api.common.visitor import visitor_key_from
from app.api.modules.activity.service import VisitorTrackingService
from app.api.modules.leads.schema import CreateLeadRequest, LeadResponse
from app.api.modules.leads.service import LeadCreationService

router = APIRouter(route_class=DishkaRoute)

logger = logging.getLogger(__name__)


@router.post(
    "",
    response_model=LeadResponse,
    status_code=201,
    dependencies=[Depends(RateLimit(LEAD_RATE_LIMIT))],
)
async def create_lead(
    request: CreateLeadRequest,
    http_request: Request,
    service: FromDishka[LeadCreationService],
    tracking: FromDishka[VisitorTrackingService],
) -> LeadResponse:
    lead = await service.create(request)
    try:
        await tracking.record_contact(
            visitor_key_from(http_request),
            name=request.name,
            phone=request.phone,
            kind="lead",
        )
    except Exception:
        logger.warning(
            "The persisted lead could not be added to visitor tracking",
            exc_info=True,
        )
    return lead
