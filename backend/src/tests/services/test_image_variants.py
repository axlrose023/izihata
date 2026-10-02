import io

import pytest
from PIL import Image

from app.api.modules.catalog.schema import image_variants_for
from app.services.image_variants import encode_variants


def image_bytes(size=(1200, 600), mode="RGBA"):
    output = io.BytesIO()
    Image.new(mode, size, (12, 34, 56, 120) if mode == "RGBA" else (12, 34, 56)).save(
        output, "PNG"
    )
    return output.getvalue()


def test_variants_preserve_ratio_transparency_and_do_not_upscale():
    content = image_bytes()
    variants = encode_variants(content)
    assert sorted(variants) == [80, 160, 320, 640, 960, 1200]
    for width, encoded in variants.items():
        with Image.open(io.BytesIO(encoded)) as image:
            assert image.size == (width, width // 2)
            assert image.mode == "RGBA"
    assert list(encode_variants(image_bytes((30, 20)))) == [30]


def test_metadata_is_ignored_after_original_image_changes():
    metadata = {"source": "old", "sizes": {"80": "thumbnail"}}
    assert image_variants_for("old", metadata) == {"80": "thumbnail"}
    assert image_variants_for("new", metadata) == {}
    assert image_variants_for(None, None) == {}


def test_invalid_images_are_rejected_without_replacing_the_original():
    with pytest.raises(OSError):
        encode_variants(b"not an image")


def test_original_bytes_are_retained_for_the_full_size_variant():
    content = image_bytes((200, 1200))
    variants = encode_variants(content)
    assert variants[200] is content
    with Image.open(io.BytesIO(variants[80])) as image:
        assert image.size == (80, 480)


@pytest.mark.asyncio
async def test_batch_limits_uploads_and_resumes_complete_metadata(monkeypatch):
    import asyncio

    from sqlalchemy import Select

    from app.api.modules.catalog.models import Product
    from app.clients.bunny_storage import BunnyS3Config
    from app.services import image_variants as module

    content = image_bytes()
    storage = BunnyS3Config(
        "https://storage.example", "zone", "test-only", "https://cdn.example"
    )
    sources = [(f"https://cdn.example/{index}.png", None) for index in range(10)]
    saved = []
    active = peak = downloads = 0

    class Rows:
        def __init__(self, values):
            self.values = values

        def all(self):
            return self.values

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def execute(self, statement):
            if isinstance(statement, Select):
                return Rows(
                    sources
                    if statement.column_descriptions[0]["entity"] is Product
                    else []
                )
            saved.append(statement.compile().params["image_variants"])

        async def commit(self):
            pass

    async def download(client, url):
        nonlocal downloads
        downloads += 1
        return content, "image/png"

    async def upload(*args):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.001)
        active -= 1

    monkeypatch.setattr(module, "download_image", download)
    monkeypatch.setattr(module, "put_object", upload)
    result = await module.generate_image_variants(
        Session, storage, concurrency=8, progress=lambda value: None
    )
    assert result["generated"] == 10
    assert 1 < peak <= 8
    assert downloads == 10
    assert len(saved) == 20
    assert all(metadata["sizes"]["1200"] == metadata["source"] for metadata in saved)
    sources = [(metadata["source"], metadata) for metadata in saved[::2]]
    downloads = 0
    result = await module.generate_image_variants(
        Session, storage, concurrency=8, progress=lambda value: None
    )
    assert result["reused"] == 10
    assert downloads == 0
