import pytest

from app.api.common.limits import MAX_JSON_BYTES


@pytest.mark.asyncio
async def test_rejects_declared_and_chunked_oversized_body(client):
    path = "/api/v1/customer-auth/register"
    declared = await client.post(
        path,
        content=b"x" * (MAX_JSON_BYTES + 1),
        headers={"content-type": "application/json"},
    )
    assert declared.status_code == 413

    async def chunks():
        yield b"x" * MAX_JSON_BYTES
        yield b"x"

    chunked = await client.post(
        path, content=chunks(), headers={"content-type": "application/json"}
    )
    assert chunked.status_code == 413


@pytest.mark.asyncio
async def test_validation_does_not_echo_input_or_password(client):
    response = await client.post(
        "/api/v1/customer-auth/register",
        json={
            "full_name": "x" * 1000000,
            "email": "invalid",
            "password": "secret",
        },
    )
    assert response.status_code == 422
    assert len(response.content) < 2000
    assert "secret" not in response.text
    assert all(
        "input" not in error and "ctx" not in error
        for error in response.json()["detail"]
    )
