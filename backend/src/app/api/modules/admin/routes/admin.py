from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends

from app.api.modules.admin.schema import DashboardResponse
from app.api.modules.admin.service import DashboardService
from app.api.modules.auth.service import AuthenticateUser
from app.api.modules.users.models import User

router = APIRouter(route_class=DishkaRoute)


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    service: FromDishka[DashboardService],
    current_user: User = Depends(AuthenticateUser()),
) -> DashboardResponse:
    return await service.get_dashboard()
