import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.api.common.exceptions import ServiceUnavailableError
from app.clients.lookup_cache import LookupCache
from app.settings import NovaPoshtaConfig

logger = logging.getLogger(__name__)
POINTS_PAGE_SIZE = 50


@dataclass(frozen=True, slots=True)
class NovaPoshtaCity:
    ref: str
    name: str
    label: str


@dataclass(frozen=True, slots=True)
class NovaPoshtaPoint:
    ref: str
    name: str
    label: str
    number: str
    type_ref: str


class NovaPoshtaClient:
    def __init__(self, config: NovaPoshtaConfig):
        self._api_key = config.api_key.get_secret_value() if config.api_key else ""
        self._client = httpx.AsyncClient(
            base_url=config.api_url,
            timeout=config.timeout_seconds,
        )
        self._cities: LookupCache[NovaPoshtaCity] = LookupCache()
        self._points: LookupCache[NovaPoshtaPoint] = LookupCache()

    async def close(self) -> None:
        await self._client.aclose()

    async def search_cities(self, search: str) -> list[NovaPoshtaCity]:
        search = " ".join(search.split()).casefold()
        return await self._cities.remember(search, lambda: self._search_cities(search))

    async def _search_cities(self, search: str) -> list[NovaPoshtaCity]:
        data = await self._call(
            model="AddressGeneral",
            method="searchSettlements",
            properties={"CityName": search, "Limit": "12", "Page": "1"},
        )
        addresses = data[0].get("Addresses", []) if data else []
        if not isinstance(addresses, list):
            raise ServiceUnavailableError(
                "Delivery address directory is temporarily unavailable",
                code="delivery_provider_unavailable",
            )
        return [
            NovaPoshtaCity(
                ref=str(item["DeliveryCity"]),
                name=str(item["MainDescription"]),
                label=str(item["Present"]),
            )
            for item in addresses
            if isinstance(item, dict)
            and item.get("DeliveryCity")
            and item.get("MainDescription")
            and item.get("Present")
        ]

    async def search_points(
        self,
        city_ref: str,
        search: str,
        type_ref: str | None = None,
        page: int = 1,
    ) -> list[NovaPoshtaPoint]:
        search = " ".join(search.split()).casefold()
        key = json.dumps([city_ref, search, type_ref, page])
        return await self._points.remember(
            key, lambda: self._search_points(city_ref, search, type_ref, page)
        )

    async def _search_points(
        self, city_ref: str, search: str, type_ref: str | None, page: int
    ) -> list[NovaPoshtaPoint]:
        properties = {
            "CityRef": city_ref,
            "Limit": str(POINTS_PAGE_SIZE),
            "Page": str(page),
        }
        if search:
            properties[
                "WarehouseId"
                if search.isascii() and search.isdigit()
                else "FindByString"
            ] = search
        if type_ref:
            properties["TypeOfWarehouseRef"] = type_ref
        data = await self._call(
            model="Address",
            method="getWarehouses",
            properties=properties,
        )
        return [
            NovaPoshtaPoint(
                ref=str(item["Ref"]),
                name=str(item["Description"]),
                label=str(item.get("ShortAddress") or item["Description"]),
                number=str(item.get("Number", "")),
                type_ref=str(item.get("TypeOfWarehouse", "")),
            )
            for item in data
            if isinstance(item, dict) and item.get("Ref") and item.get("Description")
        ]

    async def _call(
        self,
        *,
        model: str,
        method: str,
        properties: dict[str, str],
    ) -> list[dict[str, Any]]:
        try:
            request = {
                "apiKey": self._api_key,
                "modelName": model,
                "calledMethod": method,
                "methodProperties": properties,
            }
            for attempt in range(2):
                try:
                    response = await self._client.post("", json=request)
                    response.raise_for_status()
                    payload: Any = response.json()
                    if (
                        not isinstance(payload, dict)
                        or payload.get("success") is not True
                    ):
                        raise ValueError("Nova Poshta rejected the address request")
                    data = payload.get("data")
                    if not isinstance(data, list):
                        raise ValueError("Nova Poshta returned an invalid response")
                    return [item for item in data if isinstance(item, dict)]
                except (httpx.TransportError, ValueError):
                    if attempt:
                        raise
                    logger.warning("Retrying Nova Poshta lookup: method=%s", method)
                    await asyncio.sleep(0.2)
                except httpx.HTTPStatusError as exc:
                    if attempt or exc.response.status_code not in {429, 502, 503, 504}:
                        raise
                    logger.warning(
                        "Retrying Nova Poshta lookup: method=%s http=%s",
                        method,
                        exc.response.status_code,
                    )
                    await asyncio.sleep(0.2)
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning(
                "Nova Poshta lookup unavailable: method=%s error=%s",
                method,
                type(exc).__name__,
            )
            raise ServiceUnavailableError(
                "Delivery address directory is temporarily unavailable",
                code="delivery_provider_unavailable",
            ) from exc
        raise ServiceUnavailableError(
            "Delivery address directory is temporarily unavailable",
            code="delivery_provider_unavailable",
        )
