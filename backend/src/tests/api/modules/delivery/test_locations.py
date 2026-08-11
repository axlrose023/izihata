import pytest
from httpx import AsyncClient

from app.clients.nova_poshta import (
    NovaPoshtaCity,
    NovaPoshtaClient,
    NovaPoshtaPoint,
)


@pytest.mark.asyncio
class TestDeliveryLocations:
    async def test_searches_cities(
        self,
        client: AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ):
        async def search_cities(
            provider: NovaPoshtaClient,
            search: str,
        ) -> list[NovaPoshtaCity]:
            assert search == "Київ"
            return [
                NovaPoshtaCity(
                    ref="8d5a980d-391c-11dd-90d9-001a92567626",
                    name="Київ",
                    label="м. Київ, Київська обл.",
                )
            ]

        monkeypatch.setattr(NovaPoshtaClient, "search_cities", search_cities)
        response = await client.get(
            "/api/v1/delivery/cities",
            params={"search": " Київ "},
        )

        assert response.status_code == 200, response.text
        assert response.json() == [
            {
                "ref": "8d5a980d-391c-11dd-90d9-001a92567626",
                "name": "Київ",
                "label": "м. Київ, Київська обл.",
            }
        ]

    async def test_searches_and_filters_delivery_points(
        self,
        client: AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ):
        async def search_points(
            provider: NovaPoshtaClient,
            city_ref: str,
            search: str,
            type_ref: str | None = None,
        ) -> list[NovaPoshtaPoint]:
            assert city_ref == "8d5a980d-391c-11dd-90d9-001a92567626"
            assert search == "12"
            assert type_ref == "f9316480-5f2d-425d-bc2c-ac7cd29decf0"
            return [
                NovaPoshtaPoint(
                    ref="branch-ref",
                    name="Відділення №12",
                    label="вул. Хрещатик, 12",
                    number="12",
                    type_ref="841339c7-591a-42e2-8233-7a0a00f0ed6f",
                ),
                NovaPoshtaPoint(
                    ref="locker-ref",
                    name="Поштомат №2015",
                    label="вул. Хрещатик, 12",
                    number="2015",
                    type_ref="f9316480-5f2d-425d-bc2c-ac7cd29decf0",
                ),
            ]

        monkeypatch.setattr(NovaPoshtaClient, "search_points", search_points)
        response = await client.get(
            "/api/v1/delivery/points",
            params={
                "city_ref": "8d5a980d-391c-11dd-90d9-001a92567626",
                "kind": "locker",
                "search": " 12 ",
            },
        )

        assert response.status_code == 200, response.text
        assert response.json() == [
            {
                "ref": "locker-ref",
                "name": "Поштомат №2015",
                "label": "вул. Хрещатик, 12",
                "number": "2015",
            }
        ]

    async def test_rejects_invalid_city_reference(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/delivery/points",
            params={"city_ref": "invalid", "kind": "branch"},
        )

        assert response.status_code == 422
        assert response.json()["code"] == "validation_error"
