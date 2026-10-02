"""Generate immutable CDN variants; original supplier images remain intact."""

import asyncio
import hashlib
import io
import json
import logging
import time
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
GENERATOR = "webp-v3"
WIDTHS = (80, 160, 320, 640, 960, 1600)


def encode_variants(content: bytes) -> dict[int, bytes]:
    with Image.open(io.BytesIO(content)) as original:
        if original.width * original.height > 20_000_000:
            raise ValueError("Image exceeds 20 million pixels")
        if getattr(original, "is_animated", False):
            return {}
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
        # The original stays in storage; use it only if the native-size copy
        # is absent (the source exceeds 1600px) or is not smaller.
        if image.width not in result or len(result[image.width]) >= len(content):
            result[image.width] = content
        return result


async def generate_image_variants(
    sessions: async_sessionmaker,
    storage: BunnyS3Config,
    *,
    concurrency: int = 2,
    limit: int | None = None,
    upload_concurrency: int = 16,
    product_slug: str | None = None,
    progress: Callable[[str], None] = print,
) -> dict[str, int]:
    if not 1 <= concurrency <= 16:
        raise ValueError("Image processing concurrency must be between 1 and 16")
    if limit is not None and limit < 1:
        raise ValueError("Limit must be positive")
    if not 1 <= upload_concurrency <= 32:
        raise ValueError("Upload concurrency must be between 1 and 32")
    known: dict[str, dict | None] = {}
    synchronized: dict[str, bool] = {}

    def valid_metadata(source: str, metadata: dict | None) -> bool:
        return bool(
            metadata
            and metadata.get("source") == source
            and metadata.get("generator") == GENERATOR
            and metadata.get("sizes")
        )

    def register(source: str, metadata: dict | None) -> None:
        valid = valid_metadata(source, metadata)
        if source not in known:
            known[source] = metadata
            synchronized[source] = valid
        else:
            synchronized[source] = (
                synchronized[source] and valid and metadata == known[source]
            )
            if valid and not valid_metadata(source, known[source]):
                known[source] = metadata

    async with sessions() as session:
        product_id = None
        if product_slug is not None:
            product_id = await session.scalar(
                select(Product.id).where(Product.slug == product_slug)
            )
            if product_id is None:
                raise ValueError("Product not found")
        for url, metadata in (
            await session.execute(
                select(Product.image_url, Product.image_variants)
                .where(
                    Product.image_url.is_not(None),
                    *([Product.id == product_id] if product_id is not None else []),
                )
                .order_by(Product.position, Product.id)
            )
        ).all():
            register(url, metadata)
        for url, metadata in (
            await session.execute(
                select(ProductMedia.url, ProductMedia.image_variants)
                .where(
                    *(
                        [ProductMedia.product_id == product_id]
                        if product_id is not None
                        else []
                    )
                )
                .order_by(ProductMedia.product_id, ProductMedia.position)
            )
        ).all():
            register(url, metadata)
    counters = Counter(total=len(known), generated=0, reused=0, failed=0, skipped=0)
    pending = iter(list(known.items())[:limit] if limit else known.items())
    base_url = storage.public_base_url.rstrip("/")
    started = time.monotonic()
    encoding_slots = asyncio.Semaphore(2)
    upload_slots = asyncio.Semaphore(upload_concurrency)
    timeout = httpx.Timeout(30, connect=5)
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=False,
        limits=httpx.Limits(max_connections=concurrency + upload_concurrency),
    ) as client:

        async def worker() -> None:
            for source, metadata in pending:
                if not source.startswith(base_url + "/"):
                    counters["skipped"] += 1
                    continue
                try:
                    valid = valid_metadata(source, metadata)
                    if valid and synchronized[source]:
                        counters["reused"] += 1
                        continue
                    if not valid:
                        content, content_type = await with_retries(
                            lambda source=source: download_image(client, source)
                        )
                        if content_type.split(";", 1)[0] == "image/svg+xml":
                            counters["skipped"] += 1
                            continue
                        async with encoding_slots:
                            variants = await asyncio.to_thread(encode_variants, content)
                        if not variants:
                            counters["skipped"] += 1
                            continue
                        digest = hashlib.sha256(content).hexdigest()

                        async def upload(
                            width: int,
                            encoded: bytes,
                            original: bytes,
                            source_url: str,
                            digest_value: str,
                            previous_metadata: dict | None,
                        ) -> tuple[str, str] | None:
                            if encoded is original:
                                return str(width), source_url
                            if len(encoded) >= len(original):
                                return None
                            # v2 uses the same encoder for smaller sizes. Reuse
                            # those immutable files when upgrading native sizes.
                            previous_url = f"{base_url}/variants/webp-v2/{digest_value}/{width}.webp"
                            if (
                                previous_metadata
                                and previous_metadata.get("source") == source_url
                                and previous_metadata.get("generator") == "webp-v2"
                                and previous_metadata.get("sizes", {}).get(str(width))
                                == previous_url
                            ):
                                return str(width), previous_url
                            key = f"variants/{GENERATOR}/{digest_value}/{width}.webp"
                            async with upload_slots:
                                await with_retries(
                                    lambda: put_object(
                                        client, storage, key, encoded, "image/webp"
                                    )
                                )
                            return str(width), f"{base_url}/{key}"

                        uploaded = await asyncio.gather(
                            *(
                                upload(
                                    width, encoded, content, source, digest, metadata
                                )
                                for width, encoded in variants.items()
                            )
                        )
                        sizes = dict(item for item in uploaded if item is not None)
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
                    counters["elapsed_seconds"] = int(time.monotonic() - started)
                    progress(json.dumps(dict(counters)))

        await asyncio.gather(*(worker() for _ in range(concurrency)))
    counters["elapsed_seconds"] = int(time.monotonic() - started)
    progress(json.dumps(dict(counters)))
    return dict(counters)
