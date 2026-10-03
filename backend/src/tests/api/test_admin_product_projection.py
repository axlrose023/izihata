import pytest
from sqlalchemy import Engine, event


@pytest.mark.asyncio
async def test_admin_list_loads_only_table_fields(client, authenticated_user):
    statements = []

    def record(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    headers = {"Authorization": f"Bearer {authenticated_user['access_token']}"}
    event.listen(Engine, "before_cursor_execute", record)
    try:
        response = await client.get(
            "/api/v1/admin/catalog/products?page_size=100", headers=headers
        )
    finally:
        event.remove(Engine, "before_cursor_execute", record)
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert items
    assert set(items[0]) == {
        "id",
        "sku",
        "name",
        "brand",
        "price",
        "old_price",
        "stock_status",
        "is_active",
    }
    assert not any("product_attributes" in sql for sql in statements)
    product_queries = [sql for sql in statements if "FROM products" in sql]
    assert len(product_queries) == 2
    assert not any(
        "image_variants" in sql or "JOIN categories" in sql for sql in product_queries
    )
    detail = await client.get(
        "/api/v1/admin/catalog/products/" + items[0]["id"], headers=headers
    )
    assert detail.status_code == 200
    assert "specs" in detail.json() and "image_variants" in detail.json()
