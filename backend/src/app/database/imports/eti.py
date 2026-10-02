"""Supplier workbook import and Bunny Storage media transfer.

The supplier workbook is kept as the source of truth.  Product data is read
from its three sheets, while the image bytes live in Bunny Storage and only the
public CDN URLs are stored in the catalogue database.
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Final
from urllib.parse import quote, urlparse

import httpx
from openpyxl import load_workbook  # type: ignore[import-untyped]
from sqlalchemy import func, or_, select
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
from app.clients.bunny_storage import (
    MAX_IMAGE_BYTES as MAX_IMAGE_BYTES,
)
from app.clients.bunny_storage import (
    BunnyS3Config as BunnyS3Config,
)
from app.clients.bunny_storage import (
    download_image as _download_photo,
)
from app.clients.bunny_storage import (
    object_exists as _object_exists,
)
from app.clients.bunny_storage import (
    put_object as _put_object,
)
from app.clients.bunny_storage import (
    with_retries as _with_retries,
)
from app.database.imports.category_rules import FALLBACK_CATEGORY, classify

PRODUCTS_SHEET: Final = "products"
CHARACTERISTICS_SHEET: Final = "characteristics"
PHOTOS_SHEET: Final = "photos"
PRIMARY_SOURCE_LABEL: Final = "основні"
ETIM_SOURCE_LABEL: Final = "ETIM"
HAGER_PRICE_HEADER: Final = "Прайс грн. з/ПДВ"
HAGER_PHOTOS_SHEET: Final = "photo"
ENEXT_PRICE_HEADER: Final = "Ціна"
MAX_ATTRIBUTE_KEY_LENGTH: Final = 120
MAX_ATTRIBUTE_VALUE_LENGTH: Final = 1000
LEGACY_ETI_MEDIA_HOSTS: Final = frozenset({"eti.ua", "www.eti.ua"})
ETI_PIM_MEDIA_HOST: Final = "storage-api-pim.etigroup.eu"


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
    supplier_slug: str = "eti"
    kind: str = "фото"

    @property
    def object_key(self) -> str:
        extension = Path(urlparse(self.source_url).path).suffix.lower() or ".webp"
        return (
            f"products/{self.supplier_slug}/{self.sku}/{self.position + 1}{extension}"
        )


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
    sku_conflicts: list[tuple[str, str]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.created + self.updated


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
    return _read_supplier_workbook(
        path,
        price_header="Ціна в грн. з ПДВ",
        photos_sheet_name=PHOTOS_SHEET,
        has_source_column=True,
        supplier_slug="eti",
    )


def read_hager_workbook(path: Path) -> EtiWorkbook:
    """Read Hager's workbook, where all characteristics are primary."""
    return _read_supplier_workbook(
        path,
        price_header=HAGER_PRICE_HEADER,
        photos_sheet_name=HAGER_PHOTOS_SHEET,
        has_source_column=False,
        supplier_slug="hager",
    )


def read_enext_workbook(path: Path) -> EtiWorkbook:
    """Read Enext's workbook, where all characteristics are primary."""
    return _read_supplier_workbook(
        path,
        price_header=ENEXT_PRICE_HEADER,
        photos_sheet_name=HAGER_PHOTOS_SHEET,
        has_source_column=False,
        supplier_slug="enext",
    )


def read_acko_workbook(path: Path) -> EtiWorkbook:
    """Read ACKO's workbook, keeping every primary spec and image in order."""
    return _read_supplier_workbook(
        path,
        price_header=ENEXT_PRICE_HEADER,
        photos_sheet_name=HAGER_PHOTOS_SHEET,
        has_source_column=False,
        supplier_slug="acko",
    )


def _read_supplier_workbook(
    path: Path,
    *,
    price_header: str,
    photos_sheet_name: str,
    has_source_column: bool,
    supplier_slug: str,
) -> EtiWorkbook:
    """Read a supplier workbook using the shared catalogue import rules."""
    workbook = load_workbook(path, read_only=True, data_only=True)
    missing_sheets = {
        PRODUCTS_SHEET,
        CHARACTERISTICS_SHEET,
        photos_sheet_name,
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
        {"Код постачальника", "Назва товару", price_header},
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
        price = _decimal(_cell(row, product_columns[price_header]))
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
    required_characteristic_columns = {
        "Код постачальника",
        "Характеристика",
        "Значення",
        "Число",
        "Одиниця",
    }
    if has_source_column:
        required_characteristic_columns.add("Джерело")
    characteristic_columns = _column_indexes(
        characteristic_header,
        required_characteristic_columns,
        CHARACTERISTICS_SHEET,
    )
    format_index = next(
        (
            index
            for index, value in enumerate(characteristic_header)
            if _text(value) == "Формат"
        ),
        None,
    )
    specifications: dict[str, list[EtiSpecification]] = defaultdict(list)
    seen_specifications: set[tuple[str, ProductAttributeSource, str]] = set()
    positions: dict[tuple[str, ProductAttributeSource], int] = defaultdict(int)
    for row in characteristic_rows:
        sku = _supplier_code(_cell(row, characteristic_columns["Код постачальника"]))
        if sku not in products_by_sku:
            raise ValueError(f"Characteristic references unknown supplier code {sku}")
        source_label = (
            _text(_cell(row, characteristic_columns["Джерело"]))
            if has_source_column
            else PRIMARY_SOURCE_LABEL
        )
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
        numeric_value = _decimal(_cell(row, characteristic_columns["Число"]))
        if numeric_value is None and (
            format_index is None
            or _text(_cell(row, format_index)).casefold() == "число"
        ):
            numeric_value = _decimal(_cell(row, characteristic_columns["Значення"]))
        specifications[sku].append(
            EtiSpecification(
                source=source,
                key=key,
                value=value,
                position=positions[position_key],
                numeric_value=numeric_value,
            )
        )
        positions[position_key] += 1

    photo_worksheet = workbook[photos_sheet_name]
    photo_rows = photo_worksheet.iter_rows(values_only=True)
    photo_header = tuple(next(photo_rows, ()))
    photo_columns = _column_indexes(
        photo_header,
        {"Код постачальника", "URL"},
        photo_worksheet.title,
    )
    photo_type_index = next(
        (index for index, value in enumerate(photo_header) if _text(value) == "Тип"),
        None,
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
        kind = (
            _text(_cell(row, photo_type_index))
            if photo_type_index is not None
            else "фото"
        )
        if not kind:
            raise ValueError(f"Photo type is missing for supplier code {sku}")
        photos[sku].append(
            EtiPhoto(
                sku=sku,
                source_url=source_url,
                position=len(photos[sku]),
                supplier_slug=supplier_slug,
                kind=kind,
            )
        )

    return EtiWorkbook(
        products=list(products_by_sku.values()),
        specifications=dict(specifications),
        photos=dict(photos),
        duplicate_product_rows=duplicate_product_rows,
    )


def _public_url(config: BunnyS3Config, photo: EtiPhoto) -> str:
    return f"{config.public_base_url.rstrip('/')}/{quote(photo.object_key, safe='/')}"


def _pim_fallback_url(photo: EtiPhoto) -> str | None:
    """Use ETI's current PIM host if a legacy supplier URL has disappeared."""
    source = urlparse(photo.source_url)
    if source.hostname not in LEGACY_ETI_MEDIA_HOSTS or not photo.sku.isdecimal():
        return None
    identifier = photo.sku.zfill(9)
    return (
        f"https://{ETI_PIM_MEDIA_HOST}/product_db/idents/{identifier}/en-GB/photo/"
        f"{identifier}_Photo_T_BIG.webp"
    )


async def _download_eti_photo(
    client: httpx.AsyncClient,
    photo: EtiPhoto,
) -> tuple[bytes, str]:
    try:
        return await _with_retries(lambda: _download_photo(client, photo.source_url))
    except (httpx.HTTPError, ValueError):
        fallback_url = _pim_fallback_url(photo)
        if fallback_url is None:
            raise
        return await _with_retries(lambda: _download_photo(client, fallback_url))


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
                        content, content_type = await _download_eti_photo(
                            source_client,
                            photo,
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
    *,
    brand_name: str = "ETI",
    manufacturer_name: str | None = None,
) -> list[ProductAttribute]:
    reserved_keys = {"Код виробника", "Виробник"}
    if any(
        specification.source == ProductAttributeSource.PRIMARY
        and specification.key in reserved_keys
        for specification in specifications
    ):
        raise ValueError(f"Specification duplicates a reserved key for {row.sku}")
    attributes = [
        ProductAttribute(
            key="Код виробника",
            value=row.sku,
            source=ProductAttributeSource.PRIMARY,
            position=0,
        ),
        ProductAttribute(
            key="Виробник",
            value=manufacturer_name if manufacturer_name is not None else brand_name,
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
    brand_name: str = "ETI",
    manufacturer_name: str | None = None,
    sku_prefix_for_conflicts: str | None = None,
    remap_categories: bool = False,
) -> EtiImportOutcome:
    """Create or refresh a supplier range in bounded, repeatable batches."""
    if batch_size < 1:
        raise ValueError("Import batch size must be positive")
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

    source_skus = {row.sku for row in workbook.products}
    if sku_prefix_for_conflicts is not None and (
        not sku_prefix_for_conflicts
        or any(
            character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
            for character in sku_prefix_for_conflicts
        )
    ):
        raise ValueError("SKU conflict prefix contains unsupported characters")
    existing_sku_brands_query = select(Product.sku, Product.brand)
    if sku_prefix_for_conflicts is None:
        existing_sku_brands_query = existing_sku_brands_query.where(
            Product.sku.in_(source_skus)
        )
    else:
        prefix_pattern = sku_prefix_for_conflicts.replace("_", r"\_")
        existing_sku_brands_query = existing_sku_brands_query.where(
            or_(
                Product.sku.in_(source_skus),
                Product.sku.like(f"{prefix_pattern}-%", escape="\\"),
            )
        )
    existing_sku_brands: dict[str, str] = {}
    for product_sku, existing_brand in (
        await session.execute(existing_sku_brands_query)
    ).all():
        existing_sku_brands[product_sku] = existing_brand
    normalized_brand = brand_name.casefold()
    product_skus: dict[str, str] = {}
    assigned_skus: set[str] = set()
    conflicts: list[tuple[str, str]] = []
    for row in workbook.products:
        source_sku = row.sku
        existing_source_brand = existing_sku_brands.get(source_sku)
        product_sku = source_sku
        if existing_source_brand is not None and (
            existing_source_brand.casefold() != normalized_brand
        ):
            if sku_prefix_for_conflicts is None:
                conflicts.append((source_sku, existing_source_brand))
                continue

            suffix = 1
            while True:
                suffix_text = "" if suffix == 1 else f"-{suffix}"
                alias = f"{sku_prefix_for_conflicts}-{source_sku}{suffix_text}"
                suffix += 1
                if len(alias) > 64:
                    raise ValueError(
                        f"Cannot create a unique database SKU for supplier code {source_sku}"
                    )
                if alias in source_skus or alias in assigned_skus:
                    continue
                alias_brand = existing_sku_brands.get(alias)
                if alias_brand is None or alias_brand.casefold() == normalized_brand:
                    product_sku = alias
                    break
        elif existing_source_brand is None and sku_prefix_for_conflicts is not None:
            # Reuse the base conflict SKU if the other supplier stopped using it.
            alias = f"{sku_prefix_for_conflicts}-{source_sku}"
            if (
                alias not in source_skus
                and alias not in assigned_skus
                and (existing_sku_brands.get(alias) or "").casefold()
                == normalized_brand
            ):
                product_sku = alias

        product_skus[source_sku] = product_sku
        assigned_skus.add(product_sku)

    if conflicts and sku_prefix_for_conflicts is None:
        conflict_details = ", ".join(
            f"{sku} ({brand})" for sku, brand in conflicts[:10]
        )
        raise ValueError(
            f"Supplier codes already belong to another brand: {conflict_details}"
        )
    outcome.sku_conflicts = [
        (source_sku, product_sku)
        for source_sku, product_sku in product_skus.items()
        if source_sku != product_sku
    ]

    if (
        not dry_run
        and (
            await session.execute(select(Brand.id).where(Brand.name == brand_name))
        ).scalar_one_or_none()
        is None
    ):
        session.add(
            Brand(
                slug=slugify(brand_name),
                name=brand_name,
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
        replace_media_skus = set()
        if media_urls is not None:
            for row in batch:
                photos = workbook.photos.get(row.sku, [])
                if photos and all(
                    media_urls.get((photo.sku, photo.position)) for photo in photos
                ):
                    replace_media_skus.add(product_skus[row.sku])
        existing = {
            product.sku: product
            for product in (
                await session.execute(
                    select(Product)
                    .where(Product.sku.in_([product_skus[row.sku] for row in batch]))
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
                if existing_product.sku in replace_media_skus:
                    existing_product.media = []
            await session.flush()
        for row in batch:
            product_sku = product_skus[row.sku]
            category_slug, subcategory_name, matched = classify(row.name)
            category = categories.get(category_slug) or categories[FALLBACK_CATEGORY]
            subcategory = subcategories.get((category.id, subcategory_name or ""))
            product = existing.get(product_sku)
            if not matched and (product is None or remap_categories):
                outcome.unmapped.append(f"{row.sku} {row.name}")
            if product is None:
                slug = product_slug_from_sku(product_sku)
                suffix = 2
                while slug in used_slugs:
                    slug = f"{product_slug_from_sku(product_sku)}-{suffix}"
                    suffix += 1
                used_slugs.add(slug)
                product = Product(
                    category_id=category.id,
                    subcategory_id=subcategory.id if subcategory else None,
                    sku=product_sku,
                    slug=slug,
                    name=row.name,
                    brand=brand_name,
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
                    if remap_categories:
                        product.category_id = category.id
                        product.subcategory_id = subcategory.id if subcategory else None
                    product.name = row.name
                    product.brand = brand_name
                    product.price = row.price
                outcome.updated += 1

            specifications = workbook.specifications.get(row.sku, [])
            attributes = _product_attributes(
                row,
                specifications,
                brand_name=brand_name,
                manufacturer_name=manufacturer_name,
            )
            outcome.primary_specifications += sum(
                specification.source == ProductAttributeSource.PRIMARY
                for specification in attributes
            )
            outcome.etim_specifications += sum(
                specification.source == ProductAttributeSource.ETIM
                for specification in attributes
            )
            if (
                media_urls is not None
                and not dry_run
                and product_sku in replace_media_skus
            ):
                media = [
                    ProductMedia(
                        url=media_urls[(photo.sku, photo.position)],
                        alt=f"{row.name} — {photo.kind} {photo.position + 1}",
                        position=photo.position,
                    )
                    for photo in workbook.photos.get(row.sku, [])
                ]
                product.media = media
                product.image_url = media[0].url
                outcome.media_attached += len(media)
            if not dry_run:
                product.attributes = attributes

        if not dry_run:
            await session.commit()

    return outcome
