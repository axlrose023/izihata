import io

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.api.modules.catalog.models import Brand

PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000a49444154789c6360000002000100ffff03000006"
    "0005570cf5000000004945"
    "4e44ae426082"
)


@pytest.mark.asyncio
class TestPublicBrands:
    endpoint = "/api/v1/catalog/brands"

    async def test_lists_brands_that_have_products(self, client: AsyncClient):
        response = await client.get(self.endpoint)

        assert response.status_code == 200, response.text
        brands = response.json()
        assert brands
        assert all(brand["product_count"] > 0 for brand in brands)
        assert all(brand["slug"] and brand["name"] for brand in brands)

    async def test_returns_a_single_brand(self, client: AsyncClient):
        listing = await client.get(self.endpoint)
        slug = listing.json()[0]["slug"]

        response = await client.get(f"{self.endpoint}/{slug}")

        assert response.status_code == 200, response.text
        assert response.json()["slug"] == slug

    async def test_unknown_brand_is_not_found(self, client: AsyncClient):
        response = await client.get(f"{self.endpoint}/no-such-brand")

        assert response.status_code == 404


@pytest.mark.asyncio
class TestAdminBrands:
    endpoint = "/api/v1/admin/catalog/brands"

    async def test_requires_authentication(self, client: AsyncClient):
        assert (await client.get(self.endpoint)).status_code == 401

    async def test_updates_logo_and_visibility(
        self,
        client: AsyncClient,
        uow,
        authenticated_user,
    ):
        headers = {"Authorization": f"Bearer {authenticated_user['access_token']}"}
        brand = (await uow.session.execute(select(Brand).limit(1))).scalar_one()

        response = await client.patch(
            f"{self.endpoint}/{brand.id}",
            headers=headers,
            json={"logo_url": "/api/v1/media/logo.png", "position": 3},
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["logo_url"] == "/api/v1/media/logo.png"
        assert body["position"] == 3

    async def test_rejects_a_duplicate_name(
        self,
        client: AsyncClient,
        uow,
        authenticated_user,
    ):
        headers = {"Authorization": f"Bearer {authenticated_user['access_token']}"}
        brands = (await uow.session.execute(select(Brand).limit(2))).scalars().all()
        if len(brands) < 2:
            pytest.skip("needs at least two seeded brands")

        response = await client.patch(
            f"{self.endpoint}/{brands[0].id}",
            headers=headers,
            json={"name": brands[1].name},
        )

        assert response.status_code == 409


@pytest.mark.asyncio
class TestMediaUpload:
    endpoint = "/api/v1/admin/catalog/media"

    async def test_stores_a_png_and_returns_its_url(
        self,
        client: AsyncClient,
        authenticated_user,
    ):
        response = await client.post(
            self.endpoint,
            headers={"Authorization": f"Bearer {authenticated_user['access_token']}"},
            files={"file": ("logo.png", io.BytesIO(PNG_BYTES), "image/png")},
        )

        assert response.status_code == 201, response.text
        assert response.json()["url"].startswith("/api/v1/media/")

    async def test_rejects_svg(self, client: AsyncClient, authenticated_user):
        response = await client.post(
            self.endpoint,
            headers={"Authorization": f"Bearer {authenticated_user['access_token']}"},
            files={"file": ("logo.svg", io.BytesIO(b"<svg/>"), "image/svg+xml")},
        )

        assert response.status_code == 422

    async def test_requires_authentication(self, client: AsyncClient):
        response = await client.post(
            self.endpoint,
            files={"file": ("logo.png", io.BytesIO(PNG_BYTES), "image/png")},
        )

        assert response.status_code == 401
