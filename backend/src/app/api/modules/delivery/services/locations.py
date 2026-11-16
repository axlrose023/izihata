from app.api.modules.delivery.enums import DeliveryPointKind
from app.api.modules.delivery.schema import (
    DeliveryCityResponse,
    DeliveryPointPage,
    DeliveryPointResponse,
)
from app.clients.nova_poshta import POINTS_PAGE_SIZE, NovaPoshtaClient

LOCKER_TYPE_REFS = {
    "95dc212d-479c-4ffb-a8ab-8c1b9073d0bc",
    "f9316480-5f2d-425d-bc2c-ac7cd29decf0",
}
NOVA_POSHTA_LOCKER_TYPE_REF = "f9316480-5f2d-425d-bc2c-ac7cd29decf0"


class DeliveryLocationService:
    def __init__(self, client: NovaPoshtaClient):
        self._client = client

    async def search_cities(self, search: str) -> list[DeliveryCityResponse]:
        cities = await self._client.search_cities(search)
        return [
            DeliveryCityResponse(ref=city.ref, name=city.name, label=city.label)
            for city in cities
        ]

    async def search_points(
        self,
        city_ref: str,
        kind: DeliveryPointKind,
        search: str,
        page: int | None = None,
    ) -> list[DeliveryPointResponse] | DeliveryPointPage:
        needs_locker = kind == DeliveryPointKind.LOCKER
        points = await self._client.search_points(
            city_ref,
            search,
            type_ref=NOVA_POSHTA_LOCKER_TYPE_REF if needs_locker else None,
            page=page or 1,
        )
        items = [
            DeliveryPointResponse(
                ref=point.ref,
                name=point.name,
                label=point.name,
                number=point.number,
            )
            for point in points
            if (point.type_ref in LOCKER_TYPE_REFS) == needs_locker
        ]
        # Keep the existing array contract for callers without pagination.
        if page is None:
            return items
        return DeliveryPointPage(
            items=items,
            next_page=page + 1 if len(points) == POINTS_PAGE_SIZE else None,
        )
