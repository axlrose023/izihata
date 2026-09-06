"""Idempotent supplier catalogue import.

The importer takes a normalised CSV: suppliers ship every imaginable spreadsheet
format, and keeping the parsing out of the API image is deliberate. Convert the
supplier file to CSV once, then this command owns the catalogue semantics.

Rows are matched on SKU, so re-running the same file only refreshes price and
stock. Categories of existing products are never overwritten: staff may have
corrected a mapping by hand, and an import must not undo that.
"""

import csv
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.modules.catalog.enums import StockStatus
from app.api.modules.catalog.models import Category, Product, Subcategory
from app.api.modules.catalog.utils import product_slug_from_sku
from app.database.imports.category_rules import FALLBACK_CATEGORY, classify

# Supplier headers vary; every alias maps onto one canonical field.
COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "sku": ("артикул", "sku", "код", "code"),
    "name": ("найменування", "наименование", "назва", "name"),
    "stock": ("вільний залишок", "залишок", "остаток", "stock", "quantity"),
    "price": ("ціна", "цена", "price"),
}


@dataclass(frozen=True)
class ImportRow:
    sku: str
    name: str
    price: Decimal | None
    stock: int


@dataclass
class ImportOutcome:
    created: int = 0
    updated: int = 0
    skipped_without_price: list[str] = field(default_factory=list)
    unmapped: list[str] = field(default_factory=list)
    per_category: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return self.created + self.updated


def _resolve_columns(header: list[str]) -> dict[str, int]:
    normalised = [column.strip().lower() for column in header]
    resolved: dict[str, int] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for index, column in enumerate(normalised):
            if any(column.startswith(alias) for alias in aliases):
                resolved[canonical] = index
                break
    missing = {"sku", "name"} - resolved.keys()
    if missing:
        raise ValueError(
            f"CSV is missing required column(s): {', '.join(sorted(missing))}"
        )
    return resolved


def _to_decimal(raw: str) -> Decimal | None:
    text = raw.strip().replace("\xa0", "").replace(" ", "").replace(",", ".")
    if not text:
        return None
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None
    return value if value > 0 else None


def _to_int(raw: str) -> int:
    text = raw.strip().replace("\xa0", "").replace(" ", "").replace(",", ".")
    if not text:
        return 0
    try:
        return int(Decimal(text))
    except InvalidOperation:
        return 0


def read_rows(path: Path) -> list[ImportRow]:
    """Parse a supplier CSV, keeping the last row per SKU."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        try:
            dialect: type[csv.Dialect] | csv.Dialect = csv.Sniffer().sniff(
                sample, delimiters=",;\t"
            )
        except csv.Error:
            dialect = csv.excel
        reader = csv.reader(handle, dialect)
        try:
            header = next(reader)
        except StopIteration:
            return []
        columns = _resolve_columns(header)

        by_sku: dict[str, ImportRow] = {}
        for raw in reader:
            if len(raw) <= max(columns.values()):
                continue
            sku = raw[columns["sku"]].strip()
            name = raw[columns["name"]].strip()
            if not sku or not name:
                continue
            price_index = columns.get("price")
            stock_index = columns.get("stock")
            by_sku[sku] = ImportRow(
                sku=sku,
                name=name,
                price=_to_decimal(raw[price_index])
                if price_index is not None
                else None,
                stock=_to_int(raw[stock_index]) if stock_index is not None else 0,
            )
    return list(by_sku.values())


async def import_products(
    session: AsyncSession,
    rows: list[ImportRow],
    *,
    brand: str,
    activate: bool = False,
    dry_run: bool = True,
) -> ImportOutcome:
    """Create or refresh products from supplier rows.

    Imported products stay hidden unless ``activate`` is set, so a wrong
    category mapping never reaches the storefront.
    """
    outcome = ImportOutcome()

    categories = {
        category.slug: category
        for category in (await session.execute(select(Category))).scalars().all()
    }
    if FALLBACK_CATEGORY not in categories:
        raise ValueError(
            f"Fallback category '{FALLBACK_CATEGORY}' is missing from the catalog"
        )
    subcategories: dict[tuple[str, str], Subcategory] = {
        (row.category_id.hex, row.name): row
        for row in (await session.execute(select(Subcategory))).scalars().all()
    }
    existing = {
        product.sku: product
        for product in (
            await session.execute(
                # ``Product.category`` is lazy="raise", so it has to come eagerly.
                select(Product)
                .where(Product.sku.in_([row.sku for row in rows]))
                .options(joinedload(Product.category))
            )
        )
        .scalars()
        .all()
    }
    used_slugs = set((await session.execute(select(Product.slug))).scalars().all())

    for row in rows:
        if row.price is None:
            outcome.skipped_without_price.append(row.sku)
            continue

        stock_status = (
            StockStatus.IN_STOCK if row.stock > 0 else StockStatus.OUT_OF_STOCK
        )
        product = existing.get(row.sku)
        if product is not None:
            # Refresh only what the supplier is authoritative about.
            product.name = row.name
            product.price = row.price
            product.stock_status = stock_status
            outcome.updated += 1
            slug = product.category.slug
            outcome.per_category[slug] = outcome.per_category.get(slug, 0) + 1
            continue

        category_slug, subcategory_name, matched = classify(row.name)
        category = categories.get(category_slug) or categories[FALLBACK_CATEGORY]
        if not matched:
            outcome.unmapped.append(f"{row.sku} {row.name}")
        subcategory = subcategories.get((category.id.hex, subcategory_name or ""))

        slug = product_slug_from_sku(row.sku)
        suffix = 2
        while slug in used_slugs:
            slug = f"{product_slug_from_sku(row.sku)}-{suffix}"
            suffix += 1
        used_slugs.add(slug)

        outcome.created += 1
        outcome.per_category[category.slug] = (
            outcome.per_category.get(category.slug, 0) + 1
        )
        if dry_run:
            continue

        session.add(
            Product(
                category_id=category.id,
                subcategory_id=subcategory.id if subcategory else None,
                sku=row.sku,
                slug=slug,
                name=row.name,
                brand=brand,
                price=row.price,
                stock_status=stock_status,
                is_active=activate and matched,
                position=0,
            )
        )

    if not dry_run:
        await session.commit()
    return outcome
