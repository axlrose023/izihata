from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Query

from app.api.modules.delivery.enums import DeliveryPointKind
from app.api.modules.delivery.schema import (
    DeliveryCityResponse,
    DeliveryPointResponse,
)
from app.api.modules.delivery.service import DeliveryLocationService

router = APIRouter(route_class=DishkaRoute)


@router.get("/cities", response_model=list[DeliveryCityResponse])
async def search_cities(
    search: Annotated[str, Query(min_length=2, max_length=120)],
    service: FromDishka[DeliveryLocationService],
) -> list[DeliveryCityResponse]:
    return await service.search_cities(search.strip())


@router.get("/points", response_model=list[DeliveryPointResponse])
async def search_points(
    city_ref: Annotated[UUID, Query()],
    kind: Annotated[DeliveryPointKind, Query()],
    service: FromDishka[DeliveryLocationService],
    search: Annotated[str, Query(max_length=120)] = "",
) -> list[DeliveryPointResponse]:
    return await service.search_points(str(city_ref), kind, search.strip())
