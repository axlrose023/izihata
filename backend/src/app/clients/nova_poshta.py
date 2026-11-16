import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import httpx
from redis.asyncio import Redis

from app.api.common.exceptions import ServiceUnavailableError
from app.clients.nova_poshta_gate import NovaPoshtaRequestGate, directory_unavailable
from app.settings import NovaPoshtaConfig

logger = logging.getLogger(__name__)
POINTS_PAGE_SIZE = 50


@dataclass(frozen=True, slots=True)
class NovaPoshtaCity:
    ref: str
    name: str
    label: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class NovaPoshtaPoint:
    ref: str
    name: str
    label: str
    number: str
    type_ref: str
    selectable: bool = True
    city_ref: str = ""


class NovaPoshtaClient:
    def __init__(self, config: NovaPoshtaConfig, redis: Redis | None = None):
        self._api_key = config.api_key.get_secret_value() if config.api_key else ""
        self._client = httpx.AsyncClient(
            base_url=config.api_url,
            timeout=config.timeout_seconds,
        )
        self._deadline = config.request_deadline_seconds
        self._gate = NovaPoshtaRequestGate(
            redis,
            f"{config.api_url}:{self._api_key}",
            interval=config.request_interval_seconds,
            max_wait=config.request_wait_seconds,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def search_cities(self, search: str) -> list[NovaPoshtaCity]:
        search = " ".join(search.split()).casefold()
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
        return self._map_points(data)

    @staticmethod
    def _map_points(data: list[dict[str, Any]]) -> list[NovaPoshtaPoint]:
        return [
            NovaPoshtaPoint(
                ref=str(item["Ref"]),
                name=str(item["Description"]),
                label=str(item.get("ShortAddress") or item["Description"]),
                number=str(item.get("Number", "")),
                type_ref=str(item.get("TypeOfWarehouse", "")),
                selectable=str(item.get("DenyToSelect", "")).casefold()
                not in {"1", "true"}
                and str(item.get("CategoryOfWarehouse", "")).casefold()
                not in {"dropoff", "fulfillment"},
                city_ref=str(item.get("CityRef") or ""),
            )
            for item in data
            if item.get("Ref") and item.get("Description")
        ]

    async def get_points_page(
        self, city_ref: str | None, page: int, page_size: int = 500
    ) -> tuple[list[NovaPoshtaPoint], bool]:
        data = await self._call(
            model="Address",
            method="getWarehouses",
            properties={
                **({"CityRef": city_ref} if city_ref else {}),
                "Page": str(page),
                "Limit": str(page_size),
            },
        )
        points = self._map_points(data)
        if city_ref is None and any(not point.city_ref for point in points):
            raise directory_unavailable()
        return points, len(data) == page_size

    async def get_cities_page(
        self, page: int, page_size: int = 500
    ) -> tuple[list[NovaPoshtaCity], bool]:
        data = await self._call(
            model="Address",
            method="getCities",
            properties={"Page": str(page), "Limit": str(page_size)},
        )
        cities = []
        for item in data:
            if not item.get("Ref") or not item.get("Description"):
                continue
            description = str(item["Description"])
            name = description.split(" (", 1)[0].strip()
            locality = (
                f"{item.get('SettlementTypeDescription') or ''} {description}".strip()
            )
            area = str(item.get("AreaDescription") or "")
            label = locality
            if area and area.casefold() not in description.casefold():
                label = f"{locality}, {area}"
            cities.append(
                NovaPoshtaCity(
                    ref=str(item["Ref"]),
                    name=name,
                    label=label,
                    aliases=(description, str(item.get("DescriptionRu") or "")),
                )
            )
        return cities, len(data) == page_size

    async def _call(
        self,
        *,
        model: str,
        method: str,
        properties: dict[str, str],
    ) -> list[dict[str, Any]]:
        try:
            async with asyncio.timeout(self._deadline):
                return await self._request(model, method, properties)
        except (httpx.HTTPError, ValueError, TimeoutError) as exc:
            await self._gate.block(10)
            logger.warning(
                "Nova Poshta lookup unavailable: method=%s error=%s",
                method,
                type(exc).__name__,
            )
            raise directory_unavailable() from exc

    async def _request(
        self, model: str, method: str, properties: dict[str, str]
    ) -> list[dict[str, Any]]:
        request = {
            "apiKey": self._api_key,
            "modelName": model,
            "calledMethod": method,
            "methodProperties": properties,
        }
        for attempt in range(2):
            try:
                await self._gate.acquire()
                response = await self._client.post("", json=request)
                response.raise_for_status()
                payload: Any = response.json()
                if (
                    isinstance(payload, dict)
                    and payload.get("success") is not True
                    and isinstance(payload.get("errorCodes"), list)
                    and "20000401501" in payload["errorCodes"]
                    and attempt == 0
                ):
                    logger.warning("Nova Poshta key rate limit; pausing lookup")
                    await self._gate.block(1)
                if not isinstance(payload, dict) or payload.get("success") is not True:
                    raise ValueError("Nova Poshta rejected the address request")
                data = payload.get("data")
                if not isinstance(data, list) or any(
                    not isinstance(item, dict) for item in data
                ):
                    raise ValueError("Nova Poshta returned an invalid response")
                return data
            except (httpx.TransportError, ValueError):
                if attempt:
                    raise
                logger.warning("Retrying Nova Poshta lookup: method=%s", method)
                await asyncio.sleep(0.2)
            except httpx.HTTPStatusError as exc:
                if attempt or exc.response.status_code not in {429, 502, 503, 504}:
                    raise
                if exc.response.status_code == 429:
                    retry_after = exc.response.headers.get("Retry-After", "1")
                    seconds = (
                        min(10, max(1, int(retry_after)))
                        if retry_after.isascii() and retry_after.isdigit()
                        else 1
                    )
                    await self._gate.block(seconds)
                logger.warning(
                    "Retrying Nova Poshta lookup: method=%s http=%s",
                    method,
                    exc.response.status_code,
                )
                await asyncio.sleep(0.2)
        raise directory_unavailable()
