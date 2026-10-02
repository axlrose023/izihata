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


def animated_bytes():
    output = io.BytesIO()
    Image.new("RGB", (20, 20), "red").save(
        output,
        "GIF",
        save_all=True,
        append_images=[Image.new("RGB", (20, 20), "blue")],
        duration=100,
        loop=0,
    )
    return output.getvalue()


def test_animated_originals_are_preserved_without_flattening():
    assert encode_variants(animated_bytes()) == {}


def test_native_size_uses_the_smaller_copy_without_upscaling():
    content = image_bytes((200, 1200))
    variants = encode_variants(content)
    assert len(variants[200]) < len(content)
    with Image.open(io.BytesIO(variants[200])) as image:
        assert image.size == (200, 1200)
        assert image.format == "WEBP"
    with Image.open(io.BytesIO(variants[80])) as image:
        assert image.size == (80, 480)


def test_larger_native_sources_keep_the_original_without_encoding_huge_copies():
    content = image_bytes((2000, 1000))
    assert encode_variants(content)[2000] is content


def test_an_already_small_native_webp_is_not_replaced_by_a_larger_copy():
    output = io.BytesIO()
    Image.new("RGB", (200, 100), "red").save(output, "WEBP", quality=82, method=4)
    content = output.getvalue()
    assert encode_variants(content)[200] is content


@pytest.mark.asyncio
@pytest.mark.parametrize("concurrency", [2, 8, 16])
async def test_batch_limits_uploads_and_resumes_complete_metadata(
    monkeypatch, concurrency
):
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
    media_sources = []
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
                    else media_sources
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
        Session,
        storage,
        concurrency=concurrency,
        upload_concurrency=8,
        progress=lambda value: None,
    )
    assert result["generated"] == 10
    assert 1 < peak <= 8
    assert downloads == 10
    assert len(saved) == 20
    assert all(metadata["sizes"]["1200"] != metadata["source"] for metadata in saved)
    sources = [(metadata["source"], metadata) for metadata in saved[::2]]
    downloads = 0
    saved.clear()
    result = await module.generate_image_variants(
        Session,
        storage,
        concurrency=concurrency,
        upload_concurrency=8,
        progress=lambda value: None,
    )
    assert result["reused"] == 10
    assert downloads == 0
    assert saved == []

    # A valid primary copy must also repair a missing gallery reference.
    media_sources = [(sources[0][0], None)]
    saved.clear()
    result = await module.generate_image_variants(
        Session,
        storage,
        concurrency=concurrency,
        upload_concurrency=8,
        progress=lambda value: None,
    )
    assert result["reused"] == 10
    assert downloads == 0
    assert len(saved) == 2

    content = animated_bytes()
    sources = [("https://cdn.example/animated.gif", None)]
    media_sources = []
    saved.clear()
    result = await module.generate_image_variants(
        Session, storage, progress=lambda value: None
    )
    assert result["skipped"] == 1
    assert result["failed"] == result["generated"] == 0
    assert saved == []


@pytest.mark.asyncio
async def test_v2_upgrade_reuses_unchanged_derivatives_and_uploads_native_size(
    monkeypatch,
):
    import hashlib

    from sqlalchemy import Select

    from app.api.modules.catalog.models import Product
    from app.clients.bunny_storage import BunnyS3Config
    from app.services import image_variants as module

    content = image_bytes((288, 400))
    source = "https://cdn.example/original.png"
    digest = hashlib.sha256(content).hexdigest()
    metadata = {
        "source": source,
        "generator": "webp-v2",
        "sizes": {
            "80": f"https://cdn.example/variants/webp-v2/{digest}/80.webp",
            "160": f"https://cdn.example/variants/webp-v2/{digest}/160.webp",
            "288": source,
        },
    }
    saved, uploads = [], []

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
                    [(source, metadata)]
                    if statement.column_descriptions[0]["entity"] is Product
                    else []
                )
            saved.append(statement.compile().params["image_variants"])

        async def commit(self):
            pass

    async def download(client, url):
        return content, "image/png"

    async def upload(client, storage, key, encoded, content_type):
        uploads.append(key)

    monkeypatch.setattr(module, "download_image", download)
    monkeypatch.setattr(module, "put_object", upload)
    storage = BunnyS3Config(
        "https://storage.example", "zone", "test-only", "https://cdn.example"
    )
    result = await module.generate_image_variants(
        Session, storage, progress=lambda value: None
    )
    assert result["generated"] == 1
    assert uploads == [f"variants/webp-v3/{digest}/288.webp"]
    assert saved[0]["sizes"]["80"] == metadata["sizes"]["80"]
    assert saved[0]["sizes"]["160"] == metadata["sizes"]["160"]
    assert saved[0]["sizes"]["288"] != source
    assert saved[0]["generator"] == "webp-v3"
