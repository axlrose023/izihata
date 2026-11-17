import asyncio
import json
from time import monotonic
from unittest.mock import AsyncMock

import httpx
import pytest

from app.api.common.exceptions import ServiceUnavailableError
from app.clients.nova_poshta import NovaPoshtaClient
from app.clients.nova_poshta_gate import NovaPoshtaRequestGate
from app.settings import NovaPoshtaConfig


def _new_client(config: NovaPoshtaConfig | None = None) -> NovaPoshtaClient:
    client = NovaPoshtaClient(config or NovaPoshtaConfig(), AsyncMock())
    client._gate = AsyncMock(spec=NovaPoshtaRequestGate)
    return client


async def make_client(payload: object, status_code: int = 200) -> NovaPoshtaClient:
    client = _new_client(NovaPoshtaConfig())
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
    "failure", ["timeout", "503", "invalid_json", "provider_error", "key_rate_limit"]
)
async def test_retries_temporary_provider_failures(failure: str):
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            if failure == "timeout":
                raise httpx.ReadTimeout("timed out", request=request)
            if failure == "key_rate_limit":
                return httpx.Response(
                    200,
                    json={"success": False, "errorCodes": ["20000401501"], "data": []},
                    request=request,
                )
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

    client = _new_client(NovaPoshtaConfig())
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

    client = _new_client(NovaPoshtaConfig())
    await client.close()
    client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://example.test/"
    )
    try:
        assert await client.search_points("city", "390", page=2) == []
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_slow_lookup_does_not_serialize_unrelated_network_calls():
    first_started = asyncio.Event()
    second_started = asyncio.Event()
    client = _new_client(
        NovaPoshtaConfig(request_interval_seconds=0.05, request_deadline_seconds=1)
    )
    await client.close()

    async def handler(request):
        search = json.loads(request.content)["methodProperties"]["CityName"]
        if search == "first":
            first_started.set()
            await second_started.wait()
        else:
            second_started.set()
        return httpx.Response(200, json={"success": True, "data": []})

    client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://example.test/"
    )
    try:
        first = asyncio.create_task(client.search_cities("first"))
        await first_started.wait()
        assert await client.search_cities("second") == []
        assert await first == []
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_provider_request_has_an_overall_deadline():
    client = _new_client(NovaPoshtaConfig(request_deadline_seconds=1))
    await client.close()

    async def handler(request):
        await asyncio.sleep(5)
        return httpx.Response(200, json={"success": True, "data": []})

    client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://example.test/"
    )
    started = monotonic()
    try:
        with pytest.raises(ServiceUnavailableError):
            await client.search_cities("Київ")
        assert monotonic() - started < 1.5
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_marks_unselectable_points_without_losing_page_metadata():
    client = await make_client(
        {
            "success": True,
            "data": [
                {
                    "Ref": "disabled",
                    "Description": "Закрито",
                    "DenyToSelect": "1",
                    "CityRef": "city",
                },
                {"Ref": "active", "Description": "Працює", "CityRef": "city"},
            ],
        }
    )
    try:
        points, has_next = await client.get_points_page(1, page_size=2)
        assert has_next is True
        assert [point.selectable for point in points] == [False, True]
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_bulk_city_mapping_keeps_a_plain_name_and_a_distinguishing_label():
    client = await make_client(
        {
            "success": True,
            "data": [
                {
                    "Ref": "city",
                    "Description": "Абазівка (Полтавський р-н, Полтавська обл)",
                    "DescriptionRu": "Абазовка (Полтавский р-н, Полтавская обл)",
                    "AreaDescription": "Полтавська",
                    "SettlementTypeDescription": "село",
                }
            ],
        }
    )
    try:
        cities, more = await client.get_cities_page(1)
        assert more is False
        assert cities[0].name == "Абазівка"
        assert cities[0].label == "село Абазівка (Полтавський р-н, Полтавська обл)"
        assert "Абазовка" in cities[0].aliases[1]
    finally:
        await client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("city_ref", ["city-ref", None])
async def test_countrywide_points_require_a_city_reference(city_ref):
    client = await make_client(
        {
            "success": True,
            "data": [
                {"Ref": "point", "Description": "Відділення №1", "CityRef": city_ref}
            ],
        }
    )
    try:
        if city_ref is None:
            with pytest.raises(ServiceUnavailableError):
                await client.get_points_page(1)
        else:
            points, more = await client.get_points_page(1)
            assert not more
            assert points[0].city_ref == city_ref
    finally:
        await client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("directory", ["cities", "points"])
async def test_malformed_directory_page_is_not_published_as_partial_data(directory):
    client = await make_client(
        {
            "success": True,
            "data": [
                {"Ref": "valid", "Description": "Valid", "CityRef": "city"},
                {"Ref": "incomplete"},
            ],
        }
    )
    try:
        with pytest.raises(ServiceUnavailableError):
            if directory == "cities":
                await client.get_cities_page(1)
            else:
                await client.get_points_page(1)
    finally:
        await client.close()
