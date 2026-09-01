from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, Query

from app.api.modules.activity.schema import VisitorListParams, VisitorListResponse
from app.api.modules.activity.service import VisitorQueryService
from app.api.modules.auth.service import AuthenticateUser
from app.api.modules.users.models import User

router = APIRouter(route_class=DishkaRoute)


@router.get("/visitors", response_model=VisitorListResponse)
async def get_visitors(
    service: FromDishka[VisitorQueryService],
    params: Annotated[VisitorListParams, Query()],
    current_user: User = Depends(AuthenticateUser()),
) -> VisitorListResponse:
    return await service.list_visitors(params)
