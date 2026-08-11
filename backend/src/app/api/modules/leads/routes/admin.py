from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, Query

from app.api.modules.auth.service import AuthenticateUser
from app.api.modules.leads.schema import (
    AdminLeadResponse,
    LeadListParams,
    LeadListResponse,
    UpdateLeadStatusRequest,
)
from app.api.modules.leads.service import LeadManagementService
from app.api.modules.users.models import User

router = APIRouter(route_class=DishkaRoute)


@router.get("", response_model=LeadListResponse)
async def get_leads(
    service: FromDishka[LeadManagementService],
    params: Annotated[LeadListParams, Query()],
    current_user: User = Depends(AuthenticateUser()),
) -> LeadListResponse:
    return await service.list_leads(params)


@router.patch("/{lead_id}/status", response_model=AdminLeadResponse)
async def update_lead_status(
    lead_id: UUID,
    request: UpdateLeadStatusRequest,
    service: FromDishka[LeadManagementService],
    current_user: User = Depends(AuthenticateUser()),
) -> AdminLeadResponse:
    return await service.update_status(lead_id, request)
