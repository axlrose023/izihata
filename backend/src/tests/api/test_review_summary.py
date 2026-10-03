import pytest


@pytest.mark.asyncio
async def test_review_publication_and_hiding_match_summary(
    client, authenticated_user, temporary_product
):
    headers = {"Authorization": f"Bearer {authenticated_user['access_token']}"}
    path = "/api/v1/catalog/products/" + temporary_product["slug"]
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
