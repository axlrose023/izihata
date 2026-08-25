from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, Query

from app.api.modules.auth.service import AuthenticateUser
from app.api.modules.customers.schema import (
    AdminCompanyResponse,
    CompanyListParams,
    CompanyListResponse,
    ReviewCompanyRequest,
)
from app.api.modules.customers.service import CompanyManagementService
from app.api.modules.users.models import User

router = APIRouter(route_class=DishkaRoute)


@router.get("/companies", response_model=CompanyListResponse)
async def get_companies(
    service: FromDishka[CompanyManagementService],
    params: Annotated[CompanyListParams, Query()],
    current_user: User = Depends(AuthenticateUser()),
) -> CompanyListResponse:
    return await service.list_companies(params)


@router.patch("/companies/{company_id}", response_model=AdminCompanyResponse)
async def review_company(
    company_id: UUID,
    request: ReviewCompanyRequest,
    service: FromDishka[CompanyManagementService],
    current_user: User = Depends(AuthenticateUser()),
) -> AdminCompanyResponse:
    return await service.review_company(company_id, request)
