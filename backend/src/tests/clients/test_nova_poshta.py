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
    ("payload", "status_code"),
    [
        ({"success": False, "data": [], "errors": ["rejected"]}, 200),
        ({"success": True, "data": {}}, 200),
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
