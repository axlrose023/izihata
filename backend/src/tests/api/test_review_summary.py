from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_review_publication_and_hiding_match_summary(
    client, authenticated_user, product
):
    headers = {"Authorization": f"Bearer {authenticated_user['access_token']}"}
    created = await client.post(
        "/api/v1/admin/catalog/products",
        headers=headers,
        json={
            "category_id": str(product.category_id),
            "sku": "review-" + uuid4().hex,
            "name": "Review summary product",
            "brand": product.brand,
            "price": "100.00",
        },
    )
    assert created.status_code == 201, created.text
    path = "/api/v1/catalog/products/" + created.json()["slug"]
    review = await client.post(
        path + "/reviews",
        json={
            "author": "Аудит Покупець",
            "email": "review@example.com",
            "rating": 5,
            "text": "Перевірка правильного підрахунку відгуків.",
        },
    )
    assert review.status_code == 201
    moderation = "/api/v1/admin/catalog/reviews/" + review.json()["id"]
    for status, count, rating in [
        ("published", 1, "5.0"),
        ("rejected", 0, "0.0"),
        ("published", 1, "5.0"),
    ]:
        response = await client.patch(
            moderation, headers=headers, json={"status": status}
        )
        assert response.status_code == 204, response.text
        detail = (await client.get(path)).json()
        reviews = (await client.get(path + "/reviews")).json()
        assert detail["reviews_count"] == count
        assert detail["rating"] == rating
        assert len(detail["reviews"]) == count
        assert reviews["total"] == len(reviews["items"]) == count
