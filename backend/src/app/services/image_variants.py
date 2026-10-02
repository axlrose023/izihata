"""Generate immutable CDN variants; original supplier images remain intact."""

import asyncio
import hashlib
import io
import json
import logging
from collections import Counter
from collections.abc import Callable

import httpx
from PIL import Image, ImageOps
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.modules.catalog.models import Product, ProductMedia
from app.clients.bunny_storage import (
    BunnyS3Config,
    download_image,
    put_object,
    with_retries,
)

logger = logging.getLogger(__name__)
GENERATOR = "webp-v2"
WIDTHS = (80, 160, 320, 640, 960, 1600)


def encode_variants(content: bytes) -> dict[int, bytes]:
    with Image.open(io.BytesIO(content)) as original:
        if original.width * original.height > 20_000_000:
            raise ValueError("Image exceeds 20 million pixels")
        if getattr(original, "is_animated", False):
            raise ValueError("Animated originals are preserved without conversion")
        oriented = ImageOps.exif_transpose(original)
        image = oriented.convert(
            "RGBA"
            if "A" in oriented.getbands() or "transparency" in oriented.info
            else "RGB"
        )
        result: dict[int, bytes] = {}
        for width in WIDTHS:
            variant = image.copy()
            variant.thumbnail((width, image.height), Image.Resampling.LANCZOS)
            if variant.width in result:
                continue
            output = io.BytesIO()
            variant.save(output, "WEBP", quality=82, method=4)
            result[variant.width] = output.getvalue()
        # Keep an already optimized original instead of making a larger copy.
        result[image.width] = content
        return result


async def generate_image_variants(
    sessions: async_sessionmaker,
    storage: BunnyS3Config,
    *,
    concurrency: int = 2,
    limit: int | None = None,
    progress: Callable[[str], None] = print,
) -> dict[str, int]:
    if not 1 <= concurrency <= 4:
        raise ValueError("Image processing concurrency must be between 1 and 4")
    if limit is not None and limit < 1:
        raise ValueError("Limit must be positive")
    known: dict[str, dict | None] = {}
    async with sessions() as session:
        for url, metadata in (
            await session.execute(
                select(Product.image_url, Product.image_variants)
                .where(Product.image_url.is_not(None))
                .order_by(Product.position, Product.id)
            )
        ).all():
            known[url] = metadata
        for url, metadata in (
            await session.execute(
                select(ProductMedia.url, ProductMedia.image_variants).order_by(
                    ProductMedia.product_id, ProductMedia.position
                )
            )
        ).all():
            if url not in known or (not known[url] and metadata):
                known[url] = metadata
    counters = Counter(total=len(known), generated=0, reused=0, failed=0, skipped=0)
    pending = iter(list(known.items())[:limit] if limit else known.items())
    base_url = storage.public_base_url.rstrip("/")
    timeout = httpx.Timeout(30, connect=5)
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=False,
        limits=httpx.Limits(max_connections=concurrency + 1),
    ) as client:

        async def worker() -> None:
            for source, metadata in pending:
                if not source.startswith(base_url + "/"):
                    counters["skipped"] += 1
                    continue
                try:
                    valid = (
                        metadata
                        and metadata.get("source") == source
                        and metadata.get("generator") == GENERATOR
                        and metadata.get("sizes")
                    )
                    if not valid:
                        content, content_type = await with_retries(
                            lambda source=source: download_image(client, source)
                        )
                        if content_type.split(";", 1)[0] == "image/svg+xml":
                            counters["skipped"] += 1
                            continue
                        variants = await asyncio.to_thread(encode_variants, content)
                        digest = hashlib.sha256(content).hexdigest()
                        sizes = {}
                        for width, encoded in variants.items():
                            if encoded is content:
                                sizes[str(width)] = source
                                continue
                            if len(encoded) >= len(content):
                                continue
                            key = f"variants/{GENERATOR}/{digest}/{width}.webp"
                            await with_retries(
                                lambda key=key, encoded=encoded: put_object(
                                    client, storage, key, encoded, "image/webp"
                                )
                            )
                            sizes[str(width)] = f"{base_url}/{key}"
                        metadata = {
                            "source": source,
                            "generator": GENERATOR,
                            "sizes": sizes,
                        }
                    async with sessions() as session:
                        for model, column in (
                            (Product, Product.image_url),
                            (ProductMedia, ProductMedia.url),
                        ):
                            # Matching the source protects an image edited during this job.
                            await session.execute(
                                update(model)
                                .where(column == source)
                                .values(
                                    image_variants=metadata, updated_at=model.updated_at
                                )
                            )
                        await session.commit()
                    counters["reused" if valid else "generated"] += 1
                except (
                    httpx.HTTPError,
                    ValueError,
                    OSError,
                    Image.DecompressionBombError,
                ):
                    counters["failed"] += 1
                    logger.exception("Variant generation failed for %s", source)
                done = (
                    counters["generated"]
                    + counters["reused"]
                    + counters["failed"]
                    + counters["skipped"]
                )
                if done % 100 == 0:
                    progress(json.dumps(dict(counters)))

        await asyncio.gather(*(worker() for _ in range(concurrency)))
    progress(json.dumps(dict(counters)))
    return dict(counters)
