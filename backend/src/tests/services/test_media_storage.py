import io

import pytest
from fastapi import UploadFile
from PIL import Image
from starlette.datastructures import Headers

from app.api.common.exceptions import UnprocessableError
from app.api.modules.catalog.services.media import MediaStorageService


@pytest.mark.asyncio
async def test_rejects_corrupt_media_before_writing(tmp_path):
    storage = MediaStorageService(tmp_path)
    upload = UploadFile(
        io.BytesIO(b"not-an-image"),
        filename="fake.jpg",
        headers=Headers({"content-type": "image/jpeg"}),
    )
    with pytest.raises(UnprocessableError) as exc:
        await storage.store(upload)
    assert exc.value.code == "invalid_media_image"
    assert not list(tmp_path.iterdir())


@pytest.mark.asyncio
async def test_uses_real_image_format_and_idempotent_atomic_file(tmp_path):
    payload = io.BytesIO()
    Image.new("RGBA", (2, 2), (255, 255, 255, 0)).save(payload, format="PNG")
    storage = MediaStorageService(tmp_path)

    async def upload():
        return await storage.store(
            UploadFile(
                io.BytesIO(payload.getvalue()),
                filename="wrong.jpg",
                headers=Headers({"content-type": "image/jpeg"}),
            )
        )

    first = await upload()
    assert first.endswith(".png")
    assert await upload() == first
    assert len(list(tmp_path.iterdir())) == 1
    with Image.open(next(tmp_path.iterdir())) as image:
        assert image.getpixel((0, 0))[3] == 0
