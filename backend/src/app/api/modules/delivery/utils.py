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


class PointSearchIndex:
    def __init__(self, points: tuple[NovaPoshtaPoint, ...]):
        cities: dict[str, list[NovaPoshtaPoint]] = {}
        numbers: dict[tuple[str, str], list[NovaPoshtaPoint]] = {}
        self._text = {}
        for point in points:
            cities.setdefault(point.city_ref, []).append(point)
            numbers.setdefault((point.city_ref, point.number), []).append(point)
            self._text[point.ref] = normalized_address(f"{point.name} {point.label}")
        self._cities = {
            key: tuple(
                sorted(
                    value,
                    key=lambda point: (
                        int(point.number) if point.number.isdecimal() else float("inf"),
                        point.ref,
                    ),
                )
            )
            for key, value in cities.items()
        }
        self._numbers = {key: tuple(value) for key, value in numbers.items()}

    def search(
        self,
        city_ref: str,
        search: str,
        type_ref: str | None,
        page: int,
        page_size: int,
    ) -> list[NovaPoshtaPoint] | None:
        points = self._cities.get(city_ref)
        if points is None:
            return None
        query = search.strip()
        numeric = query.isascii() and query.isdigit()
        if numeric:
            points = self._numbers.get((city_ref, query), ())
        text = normalized_address(query)
        needs_locker = type_ref in LOCKER_TYPE_REFS
        matches = [
            point
            for point in points
            if point.selectable
            and (point.type_ref in LOCKER_TYPE_REFS) == needs_locker
            and (not text or numeric or text in self._text[point.ref])
        ]
        start = (page - 1) * page_size
        return matches[start : start + page_size]
