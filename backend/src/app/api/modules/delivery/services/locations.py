from app.api.modules.delivery.enums import (
    LOCKER_TYPE_REFS,
    NOVA_POSHTA_LOCKER_TYPE_REF,
    DeliveryPointKind,
)
from app.api.modules.delivery.schema import (
    DeliveryCityResponse,
    DeliveryPointPage,
    DeliveryPointResponse,
)
from app.api.modules.delivery.services.directory import DeliveryDirectoryService
from app.api.modules.delivery.utils import bounded_lookup
from app.clients.nova_poshta import POINTS_PAGE_SIZE


class DeliveryLocationService:
    def __init__(self, directory: DeliveryDirectoryService):
        self._directory = directory

    async def search_cities(self, search: str) -> list[DeliveryCityResponse]:
        cities = await bounded_lookup(self._directory.search_cities(search))
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
        points = await bounded_lookup(
            self._directory.search_points(
                city_ref,
                search,
                type_ref=NOVA_POSHTA_LOCKER_TYPE_REF if needs_locker else None,
                page=page or 1,
            )
        )
        items = [
            DeliveryPointResponse(
                ref=point.ref,
                name=point.name,
                label=point.name,
                number=point.number,
            )
            for point in points
            if point.selectable and (point.type_ref in LOCKER_TYPE_REFS) == needs_locker
        ]
        # Keep the existing array contract for callers without pagination.
        if page is None:
            return items
        return DeliveryPointPage(
            items=items,
            next_page=page + 1 if len(points) == POINTS_PAGE_SIZE else None,
        )
