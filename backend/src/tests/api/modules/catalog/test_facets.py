import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_basic_facets_match_legacy_response_without_specs(client: AsyncClient):
    params = {"category": "lowvoltage", "brand": "IEK"}
    legacy = (await client.get("/api/v1/catalog/products", params=params)).json()[
        "facets"
    ]
    response = await client.get("/api/v1/catalog/facets", params=params)
    assert response.status_code == 200, response.text
    assert response.json() == {**legacy, "specs": {}}


@pytest.mark.asyncio
async def test_spec_keys_and_values_are_paginated(client: AsyncClient):
    legacy = (await client.get("/api/v1/catalog/products")).json()["facets"]["specs"]
    keys = []
    page = 1
    while True:
        response = await client.get(
            "/api/v1/catalog/spec-facets", params={"page": page, "page_size": 2}
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body["items"]) <= 2
        keys.extend(item["value"] for item in body["items"])
        if not body["has_next"]:
            break
        page += 1
    assert keys == sorted(legacy)
    for key in keys:
        response = await client.get(
            "/api/v1/catalog/spec-facets", params={"facet_key": key, "page_size": 100}
        )
        assert response.json()["items"] == legacy[key]


@pytest.mark.asyncio
async def test_values_ignore_own_selection_and_search_on_server(client: AsyncClient):
    params = [("category", "lowvoltage"), ("spec", "Полюси:1P")]
    legacy = (await client.get("/api/v1/catalog/products", params=params)).json()[
        "facets"
    ]["specs"]["Полюси"]
    response = await client.get(
        "/api/v1/catalog/spec-facets", params=[*params, ("facet_key", "Полюси")]
    )
    assert response.json()["items"] == legacy
    searched = await client.get(
        "/api/v1/catalog/spec-facets",
        params={"facet_key": "Полюси", "facet_search": "1P"},
    )
    assert all("1p" in item["value"].lower() for item in searched.json()["items"])


@pytest.mark.asyncio
async def test_spec_page_rejects_unbounded_page_size(client: AsyncClient):
    response = await client.get(
        "/api/v1/catalog/spec-facets", params={"page_size": 101}
    )
    assert response.status_code == 422
