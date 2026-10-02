import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update


@pytest.mark.asyncio
class TestGetProducts:
    endpoint = "/api/v1/catalog/products"

    async def test_returns_paginated_products_and_facets(self, client: AsyncClient):
        response = await client.get(self.endpoint)

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 73
        assert len(body["items"]) == 10
        assert body["page"] == 1
        assert body["total_pages"] == 8
        assert body["facets"]["brands"]
        assert body["facets"]["specs"]
        assert "reviews" not in body["items"][0]

    async def test_filters_by_category_brand_stock_and_spec(
        self,
        client: AsyncClient,
    ):
        response = await client.get(
            self.endpoint,
            params=[
                ("category", "lowvoltage"),
                ("brand", "IEK"),
                ("in_stock", "true"),
                ("spec", "Полюси:1P"),
            ],
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["sku"] == "AX-10001"

    async def test_search_and_price_sort(self, client: AsyncClient):
        search = await client.get(self.endpoint, params={"search": "RESI9"})
        sorted_response = await client.get(
            self.endpoint,
            params={"category": "cable", "sort": "price_asc", "page_size": 5},
        )

        assert search.status_code == 200
        assert search.json()["total"] == 2
        prices = [float(item["price"]) for item in sorted_response.json()["items"]]
        assert prices == sorted(prices)

    async def test_filters_by_repeated_product_id(self, client: AsyncClient):
        source = await client.get(self.endpoint, params={"page_size": 2})
        expected_ids = [item["id"] for item in source.json()["items"]]

        response = await client.get(
            self.endpoint,
            params=[
                ("id", expected_ids[0]),
                ("id", expected_ids[1]),
                ("id", expected_ids[0]),
                ("page_size", "100"),
            ],
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 2
        assert {item["id"] for item in body["items"]} == set(expected_ids)

    async def test_rejects_too_many_product_ids(self, client: AsyncClient):
        response = await client.get(
            self.endpoint,
            params=[("id", str(uuid.uuid4())) for _ in range(101)],
        )

        assert response.status_code == 422

    async def test_rejects_invalid_product_id(self, client: AsyncClient):
        response = await client.get(self.endpoint, params={"id": "invalid"})

        assert response.status_code == 422

    async def test_rejects_invalid_filters(self, client: AsyncClient):
        response = await client.get(
            self.endpoint,
            params={"min_price": 100, "max_price": 10},
        )

        assert response.status_code == 422

    async def test_rejects_invalid_spec_format(self, client: AsyncClient):
        response = await client.get(self.endpoint, params={"spec": "invalid"})

        assert response.status_code == 422


@pytest.mark.asyncio
class TestFilterByBadge:
    endpoint = "/api/v1/catalog/products"

    async def test_filters_a_single_badge(self, client: AsyncClient):
        response = await client.get(self.endpoint, params={"badge": "top"})

        assert response.status_code == 200, response.text
        items = response.json()["items"]
        assert items
        assert {item["badge"] for item in items} == {"top"}

    async def test_filters_several_badges(self, client: AsyncClient):
        response = await client.get(
            self.endpoint,
            params={"badge": ["sale", "promotion", "clearance"]},
        )

        assert response.status_code == 200, response.text
        badges = {item["badge"] for item in response.json()["items"]}
        assert badges <= {"sale", "promotion", "clearance"}

    async def test_rejects_an_unknown_badge(self, client: AsyncClient):
        response = await client.get(self.endpoint, params={"badge": "nonsense"})

        assert response.status_code == 422


@pytest.mark.asyncio
class TestPopularProducts:
    endpoint = "/api/v1/catalog/products"

    @staticmethod
    async def _only_popular(uow, product) -> None:
        """The seed marks several products popular; isolate one for the test."""
        from app.api.modules.catalog.models import Product

        await uow.session.execute(update(Product).values(is_popular=False))
        product.is_popular = True
        await uow.commit()

    async def test_filters_popular_only(self, client: AsyncClient, uow):
        from app.api.modules.catalog.models import Product

        product = (await uow.session.execute(select(Product).limit(1))).scalar_one()
        await self._only_popular(uow, product)

        response = await client.get(self.endpoint, params={"is_popular": "true"})

        assert response.status_code == 200, response.text
        items = response.json()["items"]
        assert [item["id"] for item in items] == [str(product.id)]

    async def test_popular_sort_puts_flagged_products_first(
        self,
        client: AsyncClient,
        uow,
    ):
        from app.api.modules.catalog.models import Product

        product = (
            await uow.session.execute(
                select(Product).order_by(Product.position.desc()).limit(1)
            )
        ).scalar_one()
        await self._only_popular(uow, product)

        response = await client.get(
            self.endpoint, params={"sort": "popular", "page_size": 50}
        )

        assert response.status_code == 200, response.text
        ids = [item["id"] for item in response.json()["items"]]
        assert ids[0] == str(product.id)

    async def test_popularity_is_independent_of_the_badge(
        self,
        client: AsyncClient,
        uow,
    ):
        from app.api.modules.catalog.enums import ProductBadge
        from app.api.modules.catalog.models import Product

        product = (await uow.session.execute(select(Product).limit(1))).scalar_one()
        await self._only_popular(uow, product)
        product.badge = ProductBadge.SALE
        await uow.commit()

        popular = await client.get(self.endpoint, params={"is_popular": "true"})
        discounted = await client.get(self.endpoint, params={"badge": "sale"})

        assert str(product.id) in {item["id"] for item in popular.json()["items"]}
        assert str(product.id) in {item["id"] for item in discounted.json()["items"]}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            '["Тип: розетка/вилка", "розетка: 230 В"]',
            {"Тип: розетка/вилка": {"розетка: 230 В"}},
        ),
        ("Полюси:1P", {"Полюси": {"1P"}}),
    ],
)
def test_spec_filters_preserve_keys_and_legacy_links(raw, expected):
    from app.api.modules.catalog.schema import ProductListParams

    assert ProductListParams(spec=[raw]).spec_filters == expected


@pytest.mark.parametrize("raw", ['["a"]', '["a", 5]', '["", "b"]', "invalid"])
def test_spec_filters_reject_invalid_pairs(raw):
    from pydantic import ValidationError

    from app.api.modules.catalog.schema import ProductListParams

    with pytest.raises(ValidationError):
        ProductListParams(spec=[raw])


@pytest.mark.asyncio
async def test_exact_sku_search_preserves_filter_scope(client, product):
    exact = await client.get(
        "/api/v1/catalog/products",
        params={"search": product.sku.lower(), "include_facets": False},
    )
    assert exact.status_code == 200, exact.text
    assert exact.json()["total"] == 1
    assert exact.json()["items"][0]["id"] == str(product.id)
    excluded = await client.get(
        "/api/v1/catalog/products",
        params={
            "search": product.sku,
            "brand": "Missing brand",
            "include_facets": False,
        },
    )
    assert excluded.json()["total"] == 0
    scoped = await client.get(
        "/api/v1/catalog/products",
        params={
            "search": product.sku,
            "id": str(uuid.uuid4()),
            "include_facets": False,
        },
    )
    assert scoped.json()["total"] == 0
