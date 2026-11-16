import json

import httpx
import pytest

from app.api.common.exceptions import ServiceUnavailableError
from app.clients.nova_poshta import NovaPoshtaClient
from app.settings import NovaPoshtaConfig


async def make_client(payload: object, status_code: int = 200) -> NovaPoshtaClient:
    client = NovaPoshtaClient(NovaPoshtaConfig())
    await client.close()
    client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                status_code,
                json=payload,
                request=request,
            )
        ),
        base_url="https://example.test/",
    )
    return client


@pytest.mark.asyncio
async def test_maps_city_search_response():
    client = await make_client(
        {
            "success": True,
            "data": [
                {
                    "Addresses": [
                        {
                            "DeliveryCity": "city-ref",
                            "MainDescription": "Київ",
                            "Present": "м. Київ, Київська обл.",
                        },
                        {"Present": "incomplete"},
                    ]
                }
            ],
        }
    )
    try:
        cities = await client.search_cities("Київ")
    finally:
        await client.close()

    assert len(cities) == 1
    assert cities[0].ref == "city-ref"
    assert cities[0].label == "м. Київ, Київська обл."


@pytest.mark.asyncio
async def test_maps_delivery_point_response():
    client = await make_client(
        {
            "success": True,
            "data": [
                {
                    "Ref": "point-ref",
                    "Description": "Відділення №12",
                    "ShortAddress": "вул. Хрещатик, 12",
                    "Number": "12",
                    "TypeOfWarehouse": "branch-type",
                }
            ],
        }
    )
    try:
        points = await client.search_points("city-ref", "12")
    finally:
        await client.close()

    assert len(points) == 1
    assert points[0].number == "12"
    assert points[0].type_ref == "branch-type"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure", ["timeout", "503", "invalid_json", "provider_error"]
)
async def test_retries_temporary_provider_failures(failure: str):
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            if failure == "timeout":
                raise httpx.ReadTimeout("timed out", request=request)
            if failure == "invalid_json":
                return httpx.Response(
                    200, content=b"temporarily unavailable", request=request
                )
            if failure == "provider_error":
                return httpx.Response(
                    200, json={"success": False, "data": []}, request=request
                )
            return httpx.Response(503, request=request)
        return httpx.Response(200, json={"success": True, "data": []}, request=request)

    client = NovaPoshtaClient(NovaPoshtaConfig())
    await client.close()
    client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://example.test/"
    )
    try:
        assert await client.search_cities("Київ") == []
        assert attempts == 2
    finally:
        await client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "status_code"),
    [
        ({"success": False, "data": [], "errors": ["rejected"]}, 200),
        ({"success": True, "data": {}}, 200),
        ({"success": True, "data": [{"Addresses": None}]}, 200),
        ({"success": True, "data": [{"Addresses": "invalid"}]}, 200),
        ({"success": True, "data": [{"Addresses": {}}]}, 200),
        ({"success": False}, 502),
    ],
)
async def test_normalizes_provider_failures(payload: object, status_code: int):
    client = await make_client(payload, status_code)
    try:
        with pytest.raises(ServiceUnavailableError) as exc_info:
            await client.search_cities("Київ")
    finally:
        await client.close()

    assert exc_info.value.code == "delivery_provider_unavailable"


@pytest.mark.asyncio
async def test_searches_by_exact_number_and_forwards_page():
    def handler(request: httpx.Request) -> httpx.Response:
        properties = json.loads(request.content)["methodProperties"]
        assert properties["WarehouseId"] == "390"
        assert properties["Page"] == "2"
        assert "FindByString" not in properties
        return httpx.Response(200, json={"success": True, "data": []})

    client = NovaPoshtaClient(NovaPoshtaConfig())
    await client.close()
    client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://example.test/"
    )
    try:
        assert await client.search_points("city", "390", page=2) == []
    finally:
        await client.close()
