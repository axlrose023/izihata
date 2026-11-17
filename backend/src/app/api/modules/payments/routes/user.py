import json
from decimal import Decimal
from typing import Any
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError

from app.api.common.rate_limit import PAYMENT_STATUS_RATE_LIMIT, RateLimit
from app.api.modules.payments.schema import (
    PaymentAvailabilityResponse,
    PaymentStatusResponse,
    WayForPayAcknowledgement,
    WayForPayCallback,
)
from app.api.modules.payments.service import WayForPayPaymentService, WayForPayProvider

router = APIRouter(route_class=DishkaRoute)


@router.get("/availability", response_model=PaymentAvailabilityResponse)
async def payment_availability(
    provider: FromDishka[WayForPayProvider],
) -> PaymentAvailabilityResponse:
    return PaymentAvailabilityResponse(online_card_enabled=provider.enabled)


@router.post(
    "/wayforpay/callback",
    response_model=WayForPayAcknowledgement,
    include_in_schema=False,
)
async def wayforpay_callback(
    request: Request,
    service: FromDishka[WayForPayPaymentService],
) -> WayForPayAcknowledgement:
    try:
        payload: Any = json.loads(
            await request.body(),
            parse_float=Decimal,
        )
        callback = WayForPayCallback.model_validate(payload)
    except (ValueError, UnicodeDecodeError, ValidationError, TypeError) as exc:
        raise HTTPException(status_code=422, detail="Invalid payment callback") from exc
    return await service.receive_callback(callback)


@router.get(
    "/wayforpay/{attempt_id}",
    response_model=PaymentStatusResponse,
    dependencies=[Depends(RateLimit(PAYMENT_STATUS_RATE_LIMIT))],
)
async def get_wayforpay_status(
    attempt_id: UUID,
    service: FromDishka[WayForPayPaymentService],
) -> PaymentStatusResponse:
    return await service.get_status(attempt_id)
