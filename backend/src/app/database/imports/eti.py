"""ETI workbook import and Bunny Storage media transfer.

The supplier workbook is kept as the source of truth.  Product data is read
from its three sheets, while the image bytes live in Bunny Storage and only the
public CDN URLs are stored in the catalogue database.
"""

import asyncio
import hashlib
import hmac
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Final
from urllib.parse import quote, urlparse

import httpx
from openpyxl import load_workbook  # type: ignore[import-untyped]
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.modules.catalog.enums import ProductAttributeSource, StockStatus
from app.api.modules.catalog.models import (
    Brand,
    Category,
    Product,
    ProductAttribute,
    ProductMedia,
    Subcategory,
)
from app.api.modules.catalog.utils import product_slug_from_sku, slugify
from app.database.imports.category_rules import FALLBACK_CATEGORY, classify

PRODUCTS_SHEET: Final = "products"
CHARACTERISTICS_SHEET: Final = "characteristics"
PHOTOS_SHEET: Final = "photos"
PRIMARY_SOURCE_LABEL: Final = "основні"
ETIM_SOURCE_LABEL: Final = "ETIM"
MAX_IMAGE_BYTES: Final = 20 * 1024 * 1024
MAX_ATTRIBUTE_KEY_LENGTH: Final = 120
MAX_ATTRIBUTE_VALUE_LENGTH: Final = 300


@dataclass(frozen=True)
class EtiProductRow:
    sku: str
    name: str
    price: Decimal
    position: int


@dataclass(frozen=True)
class EtiSpecification:
    source: ProductAttributeSource
    key: str
    value: str
    position: int
    numeric_value: Decimal | None


@dataclass(frozen=True)
class EtiPhoto:
    sku: str
    source_url: str
    position: int

    @property
    def object_key(self) -> str:
        extension = Path(urlparse(self.source_url).path).suffix.lower() or ".webp"
        return f"products/eti/{self.sku}/{self.position + 1}{extension}"


@dataclass(frozen=True)
class EtiWorkbook:
    products: list[EtiProductRow]
    specifications: dict[str, list[EtiSpecification]]
    photos: dict[str, list[EtiPhoto]]
    duplicate_product_rows: int


@dataclass
class EtiImportOutcome:
    created: int = 0
    updated: int = 0
    primary_specifications: int = 0
    etim_specifications: int = 0
    media_attached: int = 0
    unmapped: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.created + self.updated


@dataclass(frozen=True)
class BunnyS3Config:
    endpoint: str
    storage_zone: str
    password: str
    public_base_url: str

    def __post_init__(self) -> None:
        endpoint = urlparse(self.endpoint)
        public_url = urlparse(self.public_base_url)
        if endpoint.scheme != "https" or not endpoint.netloc:
            raise ValueError("Bunny S3 endpoint must be an absolute HTTPS URL")
        if public_url.scheme != "https" or not public_url.netloc:
            raise ValueError("Bunny public media URL must be an absolute HTTPS URL")
        if not self.storage_zone or not self.password:
            raise ValueError("Bunny Storage zone and password are required")


@dataclass
class MediaUploadOutcome:
    uploaded: int = 0
    already_present: int = 0
    failed: list[str] = field(default_factory=list)
    public_urls: dict[tuple[str, int], str] = field(default_factory=dict)


def _text(value: object) -> str:
    return str(value).strip() if value is not None else ""


def _format_number(value: object) -> str:
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return _text(value)
    if decimal == decimal.to_integral():
        return str(decimal.quantize(Decimal("1")))
    return format(decimal.normalize(), "f")


def _supplier_code(value: object) -> str:
    code = _format_number(value)
    if not code:
        raise ValueError("Supplier code cannot be empty")
    return code


def _decimal(value: object) -> Decimal | None:
    text = _text(value).replace(" ", "").replace(",", ".")
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _cell(row: tuple[object, ...], index: int) -> object | None:
    return row[index] if len(row) > index else None


def _column_indexes(
    header: tuple[object, ...],
    required: set[str],
    sheet_name: str,
) -> dict[str, int]:
    indexes = {_text(value): index for index, value in enumerate(header)}
    missing = required - indexes.keys()
    if missing:
        raise ValueError(
            f"Sheet '{sheet_name}' is missing: {', '.join(sorted(missing))}"
        )
    return indexes


def _display_value(value: object, number: object, unit: object) -> str:
    text = _text(value)
    if text:
        return (
            _format_number(value) if isinstance(value, (int, float, Decimal)) else text
        )
    numeric = _format_number(number)
    if not numeric:
        return ""
    return " ".join(part for part in (numeric, _text(unit)) if part)


def read_eti_workbook(path: Path) -> EtiWorkbook:
    """Read the ETI supplier workbook without altering its source order."""
    workbook = load_workbook(path, read_only=True, data_only=True)
    missing_sheets = {
        PRODUCTS_SHEET,
        CHARACTERISTICS_SHEET,
        PHOTOS_SHEET,
    } - set(workbook.sheetnames)
    if missing_sheets:
        raise ValueError(
            "Workbook is missing required sheet(s): "
            f"{', '.join(sorted(missing_sheets))}"
        )

    products_sheet = workbook[PRODUCTS_SHEET]
    product_rows = products_sheet.iter_rows(values_only=True)
    product_header = tuple(next(product_rows, ()))
    product_columns = _column_indexes(
        product_header,
        {"Код постачальника", "Назва товару", "Ціна в грн. з ПДВ"},
        PRODUCTS_SHEET,
    )
    products_by_sku: dict[str, EtiProductRow] = {}
    duplicate_product_rows = 0
    for source_position, row in enumerate(product_rows):
        sku_value = _cell(row, product_columns["Код постачальника"])
        name = _text(_cell(row, product_columns["Назва товару"]))
        if sku_value is None and not name:
            continue
        sku = _supplier_code(sku_value)
        price = _decimal(_cell(row, product_columns["Ціна в грн. з ПДВ"]))
        if not name or price is None or price <= 0:
            raise ValueError(f"Invalid product row for supplier code {sku}")
        product = EtiProductRow(
            sku=sku,
            name=name,
            price=price,
            position=source_position,
        )
        current = products_by_sku.get(sku)
        if current is not None:
            if current.name != product.name or current.price != product.price:
                raise ValueError(f"Conflicting duplicate product code {sku}")
            duplicate_product_rows += 1
            continue
        products_by_sku[sku] = product

    characteristics_sheet = workbook[CHARACTERISTICS_SHEET]
    characteristic_rows = characteristics_sheet.iter_rows(values_only=True)
    characteristic_header = tuple(next(characteristic_rows, ()))
    characteristic_columns = _column_indexes(
        characteristic_header,
        {
            "Код постачальника",
            "Джерело",
            "Характеристика",
            "Значення",
            "Число",
            "Одиниця",
        },
        CHARACTERISTICS_SHEET,
    )
    specifications: dict[str, list[EtiSpecification]] = defaultdict(list)
    seen_specifications: set[tuple[str, ProductAttributeSource, str]] = set()
    positions: dict[tuple[str, ProductAttributeSource], int] = defaultdict(int)
    for row in characteristic_rows:
        sku = _supplier_code(_cell(row, characteristic_columns["Код постачальника"]))
        if sku not in products_by_sku:
            raise ValueError(f"Characteristic references unknown supplier code {sku}")
        source_label = _text(_cell(row, characteristic_columns["Джерело"]))
        source = (
            ProductAttributeSource.PRIMARY
            if source_label.casefold() == PRIMARY_SOURCE_LABEL
            else ProductAttributeSource.ETIM
            if source_label == ETIM_SOURCE_LABEL
            else None
        )
        if source is None:
            raise ValueError(
                f"Unknown characteristic source '{source_label}' for {sku}"
            )
        key = _text(_cell(row, characteristic_columns["Характеристика"]))
        value = _display_value(
            _cell(row, characteristic_columns["Значення"]),
            _cell(row, characteristic_columns["Число"]),
            _cell(row, characteristic_columns["Одиниця"]),
        )
        if not key or not value:
            raise ValueError(f"Invalid characteristic for supplier code {sku}")
        if len(key) > MAX_ATTRIBUTE_KEY_LENGTH:
            raise ValueError(f"Characteristic key is too long for supplier code {sku}")
        if len(value) > MAX_ATTRIBUTE_VALUE_LENGTH:
            raise ValueError(
                f"Characteristic value is too long for supplier code {sku}"
            )
        identity = (sku, source, key)
        if identity in seen_specifications:
            raise ValueError(
                f"Duplicate characteristic '{key}' for supplier code {sku}"
            )
        seen_specifications.add(identity)
        position_key = (sku, source)
        specifications[sku].append(
            EtiSpecification(
                source=source,
                key=key,
                value=value,
                position=positions[position_key],
                numeric_value=_decimal(_cell(row, characteristic_columns["Число"])),
            )
        )
        positions[position_key] += 1

    photos_sheet = workbook[PHOTOS_SHEET]
    photo_rows = photos_sheet.iter_rows(values_only=True)
    photo_header = tuple(next(photo_rows, ()))
    photo_columns = _column_indexes(
        photo_header,
        {"Код постачальника", "URL"},
        PHOTOS_SHEET,
    )
    photos: dict[str, list[EtiPhoto]] = defaultdict(list)
    for row in photo_rows:
        sku = _supplier_code(_cell(row, photo_columns["Код постачальника"]))
        if sku not in products_by_sku:
            raise ValueError(f"Photo references unknown supplier code {sku}")
        source_url = _text(_cell(row, photo_columns["URL"]))
        parsed_url = urlparse(source_url)
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            raise ValueError(f"Photo URL is invalid for supplier code {sku}")
        photos[sku].append(
            EtiPhoto(sku=sku, source_url=source_url, position=len(photos[sku]))
        )

    return EtiWorkbook(
        products=list(products_by_sku.values()),
        specifications=dict(specifications),
        photos=dict(photos),
        duplicate_product_rows=duplicate_product_rows,
    )


def _public_url(config: BunnyS3Config, photo: EtiPhoto) -> str:
    return f"{config.public_base_url.rstrip('/')}/{quote(photo.object_key, safe='/')}"


def _s3_signature(
    *,
    config: BunnyS3Config,
    method: str,
    object_key: str,
    payload: bytes,
) -> tuple[str, dict[str, str]]:
    parsed = urlparse(config.endpoint)
    host = parsed.netloc
    canonical_uri = (
        "/"
        + quote(config.storage_zone, safe="")
        + "/"
        + quote(
            object_key,
            safe="/-_.~",
        )
    )
    timestamp = datetime.now(UTC)
    amz_date = timestamp.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = timestamp.strftime("%Y%m%d")
    payload_hash = hashlib.sha256(payload).hexdigest()
    canonical_headers = (
        f"host:{host}\nx-amz-content-sha256:{payload_hash}\nx-amz-date:{amz_date}\n"
    )
    signed_headers = "host;x-amz-content-sha256;x-amz-date"
    credential_scope = f"{date_stamp}/de/s3/aws4_request"
    canonical_request = "\n".join(
        (
            method,
            canonical_uri,
            "",
            canonical_headers,
            signed_headers,
            payload_hash,
        )
    )
    string_to_sign = "\n".join(
        (
            "AWS4-HMAC-SHA256",
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode()).hexdigest(),
        )
    )

    def sign(key: bytes, value: str) -> bytes:
        return hmac.new(key, value.encode(), hashlib.sha256).digest()

    signing_key = sign(
        sign(sign(sign(f"AWS4{config.password}".encode(), date_stamp), "de"), "s3"),
        "aws4_request",
    )
    signature = hmac.new(
        signing_key,
        string_to_sign.encode(),
        hashlib.sha256,
    ).hexdigest()
    authorization = (
        "AWS4-HMAC-SHA256 "
        f"Credential={config.storage_zone}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    return (
        f"{config.endpoint.rstrip('/')}{canonical_uri}",
        {
            "Authorization": authorization,
            "Host": host,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
        },
    )


async def _download_photo(client: httpx.AsyncClient, url: str) -> tuple[bytes, str]:
    async with client.stream("GET", url) as response:
        response.raise_for_status()
        chunks: list[bytes] = []
        size = 0
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > MAX_IMAGE_BYTES:
                raise ValueError(f"Photo exceeds {MAX_IMAGE_BYTES // 1024 // 1024} MB")
            chunks.append(chunk)
        if not chunks:
            raise ValueError("Photo response is empty")
        return b"".join(chunks), response.headers.get("content-type", "image/webp")


async def _object_exists(
    client: httpx.AsyncClient,
    config: BunnyS3Config,
    object_key: str,
) -> bool:
    url, headers = _s3_signature(
        config=config,
        method="HEAD",
        object_key=object_key,
        payload=b"",
    )
    response = await client.head(url, headers=headers)
    if response.status_code == 404:
        return False
    response.raise_for_status()
    return True


async def _put_object(
    client: httpx.AsyncClient,
    config: BunnyS3Config,
    object_key: str,
    content: bytes,
    content_type: str,
) -> None:
    url, headers = _s3_signature(
        config=config,
        method="PUT",
        object_key=object_key,
        payload=content,
    )
    response = await client.put(
        url,
        content=content,
        headers={**headers, "Content-Type": content_type.split(";", 1)[0]},
    )
    response.raise_for_status()


async def _with_retries[T](operation: Callable[[], Awaitable[T]]) -> T:
    for attempt in range(3):
        try:
            return await operation()
        except (httpx.HTTPError, ValueError):
            if attempt == 2:
                raise
            await asyncio.sleep(0.4 * (2**attempt))
    raise RuntimeError("Retry loop exhausted")


async def upload_eti_media(
    workbook: EtiWorkbook,
    config: BunnyS3Config,
    *,
    concurrency: int = 8,
) -> MediaUploadOutcome:
    """Copy ETI source images to Bunny S3 and return their public CDN URLs."""
    if not 1 <= concurrency <= 32:
        raise ValueError("Media upload concurrency must be between 1 and 32")

    outcome = MediaUploadOutcome()
    semaphore = asyncio.Semaphore(concurrency)
    timeout = httpx.Timeout(60, connect=15)
    async with (
        httpx.AsyncClient(timeout=timeout, follow_redirects=True) as source_client,
        httpx.AsyncClient(timeout=timeout) as storage_client,
    ):

        async def transfer(photo: EtiPhoto) -> None:
            async with semaphore:
                try:
                    exists = await _with_retries(
                        lambda: _object_exists(storage_client, config, photo.object_key)
                    )
                    if exists:
                        outcome.already_present += 1
                    else:
                        content, content_type = await _with_retries(
                            lambda: _download_photo(source_client, photo.source_url)
                        )
                        await _with_retries(
                            lambda: _put_object(
                                storage_client,
                                config,
                                photo.object_key,
                                content,
                                content_type,
                            )
                        )
                        outcome.uploaded += 1
                    outcome.public_urls[(photo.sku, photo.position)] = _public_url(
                        config,
                        photo,
                    )
                except (httpx.HTTPError, ValueError) as error:
                    outcome.failed.append(f"{photo.sku}: {error}")

        await asyncio.gather(
            *(
                transfer(photo)
                for photos in workbook.photos.values()
                for photo in photos
            )
        )
    return outcome


def planned_media_urls(
    workbook: EtiWorkbook,
    config: BunnyS3Config,
) -> dict[tuple[str, int], str]:
    """Return CDN URLs for a prior upload without making network requests."""
    return {
        (photo.sku, photo.position): _public_url(config, photo)
        for photos in workbook.photos.values()
        for photo in photos
    }


def _product_attributes(
    row: EtiProductRow,
    specifications: list[EtiSpecification],
) -> list[ProductAttribute]:
    reserved_keys = {"Код виробника", "Виробник"}
    if any(
        specification.source == ProductAttributeSource.PRIMARY
        and specification.key in reserved_keys
        for specification in specifications
    ):
        raise ValueError(f"ETI specification duplicates a reserved key for {row.sku}")
    attributes = [
        ProductAttribute(
            key="Код виробника",
            value=row.sku,
            source=ProductAttributeSource.PRIMARY,
            position=0,
        ),
        ProductAttribute(
            key="Виробник",
            value="ETI",
            source=ProductAttributeSource.PRIMARY,
            position=1,
        ),
    ]
    attributes.extend(
        ProductAttribute(
            key=specification.key,
            value=specification.value,
            source=specification.source,
            position=(specification.position + 2)
            if specification.source == ProductAttributeSource.PRIMARY
            else specification.position,
            numeric_value=specification.numeric_value,
        )
        for specification in specifications
    )
    return attributes


async def import_eti_workbook(
    session: AsyncSession,
    workbook: EtiWorkbook,
    *,
    media_urls: dict[tuple[str, int], str] | None = None,
    dry_run: bool = True,
    batch_size: int = 200,
) -> EtiImportOutcome:
    """Create or refresh the full ETI range in bounded, repeatable batches."""
    if batch_size < 1:
        raise ValueError("ETI import batch size must be positive")
    outcome = EtiImportOutcome()
    categories = {
        category.slug: category
        for category in (await session.execute(select(Category))).scalars().all()
    }
    if FALLBACK_CATEGORY not in categories:
        raise ValueError(f"Fallback category '{FALLBACK_CATEGORY}' is missing")
    subcategories = {
        (subcategory.category_id, subcategory.name): subcategory
        for subcategory in (await session.execute(select(Subcategory))).scalars().all()
    }
    used_slugs = set((await session.execute(select(Product.slug))).scalars().all())

    if (
        not dry_run
        and (
            await session.execute(select(Brand.id).where(Brand.name == "ETI"))
        ).scalar_one_or_none()
        is None
    ):
        session.add(
            Brand(
                slug=slugify("ETI"),
                name="ETI",
                position=int(
                    (
                        await session.execute(
                            select(func.coalesce(func.max(Brand.position), -1))
                        )
                    ).scalar_one()
                    + 1
                ),
                is_active=True,
            )
        )

    for start in range(0, len(workbook.products), batch_size):
        batch = workbook.products[start : start + batch_size]
        existing = {
            product.sku: product
            for product in (
                await session.execute(
                    select(Product)
                    .where(Product.sku.in_([row.sku for row in batch]))
                    .options(
                        selectinload(Product.attributes),
                        selectinload(Product.media),
                    )
                )
            )
            .scalars()
            .all()
        }
        if not dry_run and existing:
            # PostgreSQL may otherwise INSERT the replacement rows before it
            # DELETEs the old rows, which violates the per-source key and media
            # position constraints on a repeat import.
            for existing_product in existing.values():
                existing_product.attributes = []
                if media_urls is not None:
                    existing_product.media = []
            await session.flush()
        for row in batch:
            category_slug, subcategory_name, matched = classify(row.name)
            category = categories.get(category_slug) or categories[FALLBACK_CATEGORY]
            subcategory = subcategories.get((category.id, subcategory_name or ""))
            if not matched:
                outcome.unmapped.append(f"{row.sku} {row.name}")
            product = existing.get(row.sku)
            if product is None:
                slug = product_slug_from_sku(row.sku)
                suffix = 2
                while slug in used_slugs:
                    slug = f"{product_slug_from_sku(row.sku)}-{suffix}"
                    suffix += 1
                used_slugs.add(slug)
                product = Product(
                    category_id=category.id,
                    subcategory_id=subcategory.id if subcategory else None,
                    sku=row.sku,
                    slug=slug,
                    name=row.name,
                    brand="ETI",
                    price=row.price,
                    stock_status=StockStatus.PREORDER,
                    stock_quantity=0,
                    is_active=True,
                    position=row.position,
                    attributes=[],
                    media=[],
                )
                outcome.created += 1
                if not dry_run:
                    session.add(product)
            else:
                if not dry_run:
                    product.category_id = category.id
                    product.subcategory_id = subcategory.id if subcategory else None
                    product.name = row.name
                    product.brand = "ETI"
                    product.price = row.price
                    product.stock_status = StockStatus.PREORDER
                    product.stock_quantity = 0
                    product.is_active = True
                    product.position = row.position
                outcome.updated += 1

            specifications = workbook.specifications.get(row.sku, [])
            attributes = _product_attributes(row, specifications)
            outcome.primary_specifications += sum(
                specification.source == ProductAttributeSource.PRIMARY
                for specification in attributes
            )
            outcome.etim_specifications += sum(
                specification.source == ProductAttributeSource.ETIM
                for specification in attributes
            )
            if media_urls is not None and not dry_run:
                media = [
                    ProductMedia(
                        url=media_urls[(photo.sku, photo.position)],
                        alt=f"{row.name} — фото {photo.position + 1}",
                        position=photo.position,
                    )
                    for photo in workbook.photos.get(row.sku, [])
                    if (photo.sku, photo.position) in media_urls
                ]
                product.media = media
                product.image_url = media[0].url if media else None
                outcome.media_attached += len(media)
            if not dry_run:
                product.attributes = attributes

        if not dry_run:
            await session.commit()

    return outcome
