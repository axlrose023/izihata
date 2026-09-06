import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete, select

from app.api.modules.catalog.models import Product


@pytest.mark.asyncio
class TestProductVisibility:
    admin_endpoint = "/api/v1/admin/catalog/products"
    public_endpoint = "/api/v1/catalog/products"

    @pytest_asyncio.fixture(autouse=True)
    async def _clean_slate(self, uow):
        """The suite shares one database, so these products must not outlive the test."""

        async def purge() -> None:
            await uow.session.execute(delete(Product).where(Product.sku.like("VIS-%")))
            await uow.commit()

        await purge()
        yield
        await purge()

    @staticmethod
    def _headers(authenticated_user) -> dict[str, str]:
        return {"Authorization": f"Bearer {authenticated_user['access_token']}"}

    async def _create(self, client: AsyncClient, uow, headers, **overrides):
        category_id = str(
            (
                await uow.session.execute(select(Product.category_id).limit(1))
            ).scalar_one()
        )
        payload = {
            "category_id": category_id,
            "sku": overrides.pop("sku", "VIS-1"),
            "name": "Товар для перевірки видимості",
            "brand": "ETI",
            "price": "199.00",
            "specs": {},
            **overrides,
        }
        response = await client.post(self.admin_endpoint, headers=headers, json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    async def test_products_are_visible_by_default(
        self, client: AsyncClient, uow, authenticated_user
    ):
        headers = self._headers(authenticated_user)
        created = await self._create(client, uow, headers, sku="VIS-DEFAULT")

        assert created["is_active"] is True

    async def test_a_hidden_product_never_reaches_the_storefront(
        self, client: AsyncClient, uow, authenticated_user
    ):
        headers = self._headers(authenticated_user)
        created = await self._create(
            client, uow, headers, sku="VIS-HIDDEN", is_active=False
        )

        assert created["is_active"] is False
        listing = await client.get(self.public_endpoint, params={"page_size": 100})
        assert created["id"] not in {i["id"] for i in listing.json()["items"]}
        detail = await client.get(f"{self.public_endpoint}/{created['slug']}")
        assert detail.status_code == 404

    async def test_staff_can_still_find_and_reactivate_a_hidden_product(
        self, client: AsyncClient, uow, authenticated_user
    ):
        headers = self._headers(authenticated_user)
        created = await self._create(
            client, uow, headers, sku="VIS-REVIVE", is_active=False
        )

        # It must remain visible to staff, otherwise hiding is a one-way door.
        listing = await client.get(
            self.admin_endpoint, headers=headers, params={"search": "VIS-REVIVE"}
        )
        assert listing.status_code == 200, listing.text
        assert created["id"] in {item["id"] for item in listing.json()["items"]}

        detail = await client.get(
            f"{self.admin_endpoint}/{created['id']}", headers=headers
        )
        assert detail.status_code == 200

        revived = await client.patch(
            f"{self.admin_endpoint}/{created['id']}",
            headers=headers,
            json={"is_active": True},
        )
        assert revived.status_code == 200, revived.text
        assert revived.json()["is_active"] is True

        public = await client.get(f"{self.public_endpoint}/{created['slug']}")
        assert public.status_code == 200

    async def test_admin_listing_can_filter_by_visibility(
        self, client: AsyncClient, uow, authenticated_user
    ):
        headers = self._headers(authenticated_user)
        hidden = await self._create(
            client, uow, headers, sku="VIS-FILTER", is_active=False
        )

        response = await client.get(
            self.admin_endpoint,
            headers=headers,
            params={"is_active": "false", "page_size": 100},
        )

        assert response.status_code == 200, response.text
        items = response.json()["items"]
        assert hidden["id"] in {item["id"] for item in items}
        assert all(item["is_active"] is False for item in items)

    async def test_admin_listing_requires_authentication(self, client: AsyncClient):
        assert (await client.get(self.admin_endpoint)).status_code == 401
