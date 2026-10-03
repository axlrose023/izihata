import io

import pytest
from PIL import Image
from httpx import AsyncClient
from sqlalchemy import select

from app.api.modules.catalog.models import Brand

_png = io.BytesIO()
Image.new("RGBA", (1, 1), (255, 255, 255, 0)).save(_png, format="PNG")
PNG_BYTES = _png.getvalue()


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

    async def test_rename_preserves_product_membership_and_slug(
        self, client, uow, authenticated_user
    ):
        from app.api.modules.catalog.models import Product

        headers = {"Authorization": f"Bearer {authenticated_user['access_token']}"}
        brand = (
            await uow.session.execute(select(Brand).where(Brand.name == "IEK"))
        ).scalar_one()
        old_name, old_slug = brand.name, brand.slug
        before = (await client.get(f"/api/v1/catalog/brands/{old_slug}")).json()[
            "product_count"
        ]
        try:
            response = await client.patch(
                f"{self.endpoint}/{brand.id}",
                headers=headers,
                json={"name": "IEK renamed regression"},
            )
            assert response.status_code == 200, response.text
            assert response.json()["product_count"] == before
            assert response.json()["slug"] == old_slug
            listing = await client.get(
                "/api/v1/catalog/products",
                params={"brand": "IEK renamed regression", "include_facets": False},
            )
            assert listing.json()["total"] == before
            assert (
                await uow.session.execute(
                    select(Product).where(Product.brand == old_name)
                )
            ).scalars().all() == []
        finally:
            await client.patch(
                f"{self.endpoint}/{brand.id}", headers=headers, json={"name": old_name}
            )


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

    async def test_rejects_an_oversized_image(
        self, client: AsyncClient, authenticated_user
    ):
        oversized = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * (8 * 1024 * 1024 + 1))

        response = await client.post(
            self.endpoint,
            headers={"Authorization": f"Bearer {authenticated_user['access_token']}"},
            files={"file": ("big.png", oversized, "image/png")},
        )

        assert response.status_code == 422
        assert response.json()["code"] == "media_too_large"

    async def test_names_the_rejected_type(
        self, client: AsyncClient, authenticated_user
    ):
        response = await client.post(
            self.endpoint,
            headers={"Authorization": f"Bearer {authenticated_user['access_token']}"},
            files={"file": ("photo.heic", io.BytesIO(b"heic"), "image/heic")},
        )

        assert response.status_code == 422
        assert "image/heic" in response.json()["detail"]

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
