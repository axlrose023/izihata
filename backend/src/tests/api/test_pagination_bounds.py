import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.api.common.schema import PaginationParams
from app.settings import get_config


def test_largest_supported_offset_fits_in_signed_bigint():
    size = get_config().api.page_max_size
    page = ((1 << 63) - 1) // size + 1
    assert PaginationParams(page=page, page_size=size).offset < 1 << 63
    with pytest.raises(ValidationError):
        PaginationParams(page=page + 1)


@pytest.mark.asyncio
async def test_catalog_rejects_overflowing_pages_instead_of_500(client: AsyncClient):
    response = await client.get(
        "/api/v1/catalog/products",
        params={"page": str(1 << 63), "page_size": 100, "include_facets": "false"},
    )
    assert response.status_code == 422
