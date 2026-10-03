import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize("search", ["%%", "__"])
async def test_user_wildcards_do_not_match_unrelated_products(
    client, authenticated_user, product, search
):
    response = await client.get(
        "/api/v1/catalog/products", params={"search": search, "include_facets": "false"}
    )
    assert response.status_code == 200
    assert all(item["id"] != str(product.id) for item in response.json()["items"])
    response = await client.get(
        "/api/v1/admin/catalog/products",
        headers={"Authorization": f"Bearer {authenticated_user['access_token']}"},
        params={"search": search},
    )
    assert response.status_code == 200
    assert all(item["id"] != str(product.id) for item in response.json()["items"])
