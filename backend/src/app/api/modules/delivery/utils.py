"""Address matching, pagination and the public lookup deadline."""

import asyncio
import re
from collections import OrderedDict
from collections.abc import Awaitable

from app.api.modules.delivery.enums import LOCKER_TYPE_REFS
from app.clients.nova_poshta import NovaPoshtaCity, NovaPoshtaPoint
from app.clients.nova_poshta_gate import directory_unavailable


async def bounded_lookup[T](operation: Awaitable[T], *, seconds: float = 10) -> T:
    try:
        async with asyncio.timeout(seconds):
            return await operation
    except TimeoutError as exc:
        raise directory_unavailable() from exc


def normalized_address(value: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", value.casefold()).split())


class CitySearchIndex:
    def __init__(self, cities: tuple[NovaPoshtaCity, ...]):
        self._entries = [
            (
                city,
                tuple(normalized_address(name) for name in (city.name, *city.aliases)),
                normalized_address(city.label),
            )
            for city in cities
        ]
        self._queries: OrderedDict[str, tuple[NovaPoshtaCity, ...]] = OrderedDict()

    def search(self, search: str) -> list[NovaPoshtaCity]:
        query = normalized_address(search)
        if not query:
            return []
        if query in self._queries:
            self._queries.move_to_end(query)
            return list(self._queries[query])
        matches = []
        for city, names, label in self._entries:
            if any(query in name for name in names) or query in label:
                rank = (
                    0
                    if query in names
                    else 1
                    if any(name.startswith(query) for name in names)
                    else 2
                )
                matches.append((rank, city.name, city))
        matches.sort(key=lambda item: (item[0], item[1]))
        result = tuple(item[2] for item in matches[:12])
        self._queries[query] = result
        while len(self._queries) > 256:
            self._queries.popitem(last=False)
        return list(result)


def match_points(
    points: tuple[NovaPoshtaPoint, ...],
    search: str,
    type_ref: str | None,
    page: int,
    page_size: int,
) -> list[NovaPoshtaPoint]:
    query = normalized_address(search)
    numeric = search.strip().isascii() and search.strip().isdigit()
    selected = [
        point
        for point in points
        if point.selectable
        and (point.type_ref in LOCKER_TYPE_REFS) == (type_ref in LOCKER_TYPE_REFS)
        and (
            not query
            or (numeric and point.number == search.strip())
            or (
                not numeric
                and query in normalized_address(f"{point.name} {point.label}")
            )
        )
    ]
    start = (page - 1) * page_size
    return selected[start : start + page_size]
