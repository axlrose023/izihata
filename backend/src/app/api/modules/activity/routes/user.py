from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, Request, Response, status

from app.api.common.rate_limit import ACTIVITY_RATE_LIMIT, RateLimit
from app.api.common.visitor import (
    VISITOR_COOKIE,
    VISITOR_COOKIE_MAX_AGE,
    visitor_key_from,
)
from app.api.modules.activity.schema import TrackVisitRequest
from app.api.modules.activity.service import VisitorTrackingService
from app.api.modules.customers.models import Customer
from app.api.modules.customers.service import OptionalAuthenticateCustomer

router = APIRouter(route_class=DishkaRoute)


@router.post(
    "/visits",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RateLimit(ACTIVITY_RATE_LIMIT))],
)
async def track_visit(
    request: TrackVisitRequest,
    http_request: Request,
    response: Response,
    service: FromDishka[VisitorTrackingService],
    customer: Customer | None = Depends(OptionalAuthenticateCustomer()),
) -> None:
    key = await service.track(
        visitor_key_from(http_request),
        request,
        user_agent=http_request.headers.get("user-agent", "")[:400] or None,
        customer_id=customer.id if customer is not None else None,
    )
    response.set_cookie(
        VISITOR_COOKIE,
        str(key),
        max_age=VISITOR_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=http_request.url.scheme == "https",
    )
