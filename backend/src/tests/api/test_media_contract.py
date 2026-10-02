import pytest
from pydantic import ValidationError

from app.api.modules.catalog.schema import UpdateProductRequest


def test_update_accepts_existing_large_galleries_without_truncation():
    media = [
        {
            "url": f"https://images.example/{index}.jpg",
            "alt": "Photo",
            "position": index,
        }
        for index in range(22)
    ]
    request = UpdateProductRequest(media=media)
    assert len(request.media) == 22
    assert [item.url for item in request.media] == [item["url"] for item in media]
    with pytest.raises(ValidationError):
        UpdateProductRequest(media=media * 5)
