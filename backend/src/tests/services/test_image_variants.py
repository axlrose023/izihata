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
