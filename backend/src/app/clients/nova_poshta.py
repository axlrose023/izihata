from dataclasses import dataclass
from typing import Any

import httpx

from app.api.common.exceptions import ServiceUnavailableError
from app.settings import NovaPoshtaConfig


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

    async def close(self) -> None:
        await self._client.aclose()

    async def search_cities(self, search: str) -> list[NovaPoshtaCity]:
        data = await self._call(
            model="AddressGeneral",
            method="searchSettlements",
            properties={"CityName": search, "Limit": "12", "Page": "1"},
        )
        addresses = data[0].get("Addresses", []) if data else []
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
    ) -> list[NovaPoshtaPoint]:
        properties = {"CityRef": city_ref, "Limit": "50", "Page": "1"}
        if search:
            properties["FindByString"] = search
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
            response = await self._client.post(
                "",
                json={
                    "apiKey": self._api_key,
                    "modelName": model,
                    "calledMethod": method,
                    "methodProperties": properties,
                },
            )
            response.raise_for_status()
            payload: Any = response.json()
            if not isinstance(payload, dict) or payload.get("success") is not True:
                raise ValueError("Nova Poshta rejected the address request")
            data = payload.get("data")
            if not isinstance(data, list):
                raise ValueError("Nova Poshta returned an invalid response")
            return [item for item in data if isinstance(item, dict)]
        except (httpx.HTTPError, ValueError) as exc:
            raise ServiceUnavailableError(
                "Delivery address directory is temporarily unavailable",
                code="delivery_provider_unavailable",
            ) from exc
