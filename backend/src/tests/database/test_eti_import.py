from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest
import pytest_asyncio
from openpyxl import Workbook
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.api.modules.catalog.enums import ProductAttributeSource, StockStatus
from app.api.modules.catalog.models import Brand, Category, Product, ProductMedia
from app.database.imports import (
    BunnyS3Config,
    import_eti_workbook,
    planned_media_urls,
    read_acko_workbook,
    read_enext_workbook,
    read_eti_workbook,
)
from app.database.imports.eti import EtiPhoto, _pim_fallback_url


def test_pim_fallback_repairs_legacy_eti_photo_url() -> None:
    photo = EtiPhoto(
        sku="4774033",
        source_url=(
            "https://www.eti.ua/product_db/idents/004774033/en-GB/photo/"
            "004774033_Photo_T_BIG.webp"
        ),
        position=0,
    )

    assert _pim_fallback_url(photo) == (
        "https://storage-api-pim.etigroup.eu/product_db/idents/004774033/en-GB/"
        "photo/004774033_Photo_T_BIG.webp"
    )


def write_workbook(path: Path) -> Path:
    workbook = Workbook()
    products = workbook.active
    products.title = "products"
    products.append(["Код постачальника", "Назва товару", "Ціна в грн. з ПДВ"])
    products.append(["ETI-TEST-1", "Авт. вимикач ETIMAT 6 1p C16", 120.5])
    products.append(["ETI-TEST-1", "Авт. вимикач ETIMAT 6 1p C16", 120.5])

    characteristics = workbook.create_sheet("characteristics")
    characteristics.append(
        [
            "Код постачальника",
            "Джерело",
            "Характеристика",
            "Значення",
            "Число",
            "Одиниця",
        ]
    )
    characteristics.append(["ETI-TEST-1", "основні", "Полюси", "1P", None, None])
    characteristics.append(["ETI-TEST-1", "основні", "Номінал", None, 16, "А"])
    characteristics.append(["ETI-TEST-1", "ETIM", "Ширина", None, 18, "мм"])

    photos = workbook.create_sheet("photos")
    photos.append(["Код постачальника", "URL"])
    photos.append(["ETI-TEST-1", "https://supplier.example/one.webp"])
    photos.append(["ETI-TEST-1", "https://supplier.example/two.webp"])
    workbook.save(path)
    return path


def write_enext_workbook(path: Path) -> Path:
    workbook = Workbook()
    products = workbook.active
    products.title = "products"
    products.append(["Код постачальника", "Назва товару", "Ціна", "Од."])
    products.append(["ENEXT-TEST-1", "Автоматичний вимикач тестовий", 120.5, "шт"])

    characteristics = workbook.create_sheet("characteristics")
    characteristics.append(
        ["Код постачальника", "Характеристика", "Значення", "Число", "Одиниця"]
    )
    long_value = "Технічна характеристика " + "x" * 350
    characteristics.append(["ENEXT-TEST-1", "Опис", long_value, None, None])

    photos = workbook.create_sheet("photo")
    photos.append(["Код постачальника", "URL"])
    photos.append(["ENEXT-TEST-1", "https://enext.ua/one.webp"])
    photos.append(["ENEXT-TEST-1", "https://enext.ua/two.webp"])
    workbook.save(path)
    return path


def write_acko_workbook(path: Path) -> Path:
    workbook = Workbook()
    products = workbook.active
    products.title = "products"
    products.append(["Код постачальника", "Назва товару", "Ціна", "Од."])
    products.append(["ACKO-TEST-1", "Автоматичний вимикач ACKO", 123.45, "шт"])

    characteristics = workbook.create_sheet("characteristics")
    characteristics.append(
        [
            "Код постачальника",
            "Характеристика",
            "Значення",
            "Одиниця",
            "Число",
            "Число до",
            "Формат",
        ]
    )
    long_value = "x" * 767
    characteristics.append(
        ["ACKO-TEST-1", "Особливості", long_value, None, None, None, "текст"]
    )
    characteristics.append(
        ["ACKO-TEST-1", "Об'єм", "0,00014", "м³", 0.00014, None, "число"]
    )
    characteristics.append(
        [
            "ACKO-TEST-1",
            "Набір матриць",
            "162535507095120150185240300400",
            None,
            None,
            None,
            "текст",
        ]
    )

    photos = workbook.create_sheet("photo")
    photos.append(["Код постачальника", "Тип", "URL"])
    photos.append(["ACKO-TEST-1", "фото", "https://acko.ua/one.jpeg"])
    photos.append(["ACKO-TEST-1", "схема", "https://acko.ua/two.png"])
    workbook.save(path)
    return path


@pytest.mark.asyncio
class TestEtiWorkbookImport:
    @pytest_asyncio.fixture(autouse=True)
    async def _clean_slate(self, uow):
        await uow.session.execute(
            delete(Product).where(
                Product.sku.in_(
                    {
                        "ETI-TEST-1",
                        "ACKO-TEST-1",
                        "ACKO-ACKO-TEST-1",
                    }
                )
            )
        )
        await uow.commit()
        yield
        await uow.session.execute(
            delete(Product).where(
                Product.sku.in_(
                    {
                        "ETI-TEST-1",
                        "ACKO-TEST-1",
                        "ACKO-ACKO-TEST-1",
                    }
                )
            )
        )
        await uow.commit()

    async def test_imports_primary_and_etim_specs_with_all_media(self, tmp_path, uow):
        workbook = read_eti_workbook(write_workbook(tmp_path / "eti.xlsx"))
        config = BunnyS3Config(
            endpoint="https://de-s3.storage.bunnycdn.com",
            storage_zone="izihata-product-media",
            password="test-password",
            public_base_url="https://izihata-product-media.b-cdn.net",
        )

        outcome = await import_eti_workbook(
            uow.session,
            workbook,
            media_urls=planned_media_urls(workbook, config),
            dry_run=False,
            batch_size=1,
        )

        product = (
            await uow.session.execute(
                select(Product)
                .where(Product.sku == "ETI-TEST-1")
                .options(selectinload(Product.attributes), selectinload(Product.media))
            )
        ).scalar_one()
        primary = [
            attribute
            for attribute in product.attributes
            if attribute.source == ProductAttributeSource.PRIMARY
        ]
        etim = [
            attribute
            for attribute in product.attributes
            if attribute.source == ProductAttributeSource.ETIM
        ]

        assert (outcome.created, outcome.updated) == (1, 0)
        assert workbook.duplicate_product_rows == 1
        assert product.brand == "ETI"
        assert product.stock_status == StockStatus.PREORDER
        assert product.is_active is True
        assert [(item.key, item.value) for item in primary] == [
            ("Код виробника", "ETI-TEST-1"),
            ("Виробник", "ETI"),
            ("Полюси", "1P"),
            ("Номінал", "16 А"),
        ]
        assert [(item.key, item.value) for item in etim] == [("Ширина", "18 мм")]
        assert [media.url for media in product.media] == [
            "https://izihata-product-media.b-cdn.net/products/eti/ETI-TEST-1/1.webp",
            "https://izihata-product-media.b-cdn.net/products/eti/ETI-TEST-1/2.webp",
        ]
        assert product.image_url == product.media[0].url

        product.image_variants = {
            "source": product.image_url,
            "generator": "webp-v2",
            "sizes": {"80": "https://cdn.example/stale.webp"},
        }
        await uow.commit()

        repeated = await import_eti_workbook(
            uow.session,
            workbook,
            media_urls=planned_media_urls(workbook, config),
            dry_run=False,
            batch_size=1,
        )
        assert (repeated.created, repeated.updated) == (0, 1)
        await uow.session.refresh(product)
        assert product.image_variants is None

    async def test_dry_run_does_not_write_products(self, tmp_path, uow):
        workbook = read_eti_workbook(write_workbook(tmp_path / "eti.xlsx"))

        outcome = await import_eti_workbook(uow.session, workbook, dry_run=True)

        stored = (
            await uow.session.execute(
                select(Product).where(Product.sku == "ETI-TEST-1")
            )
        ).scalar_one_or_none()
        assert outcome.created == 1
        assert stored is None

    async def test_reimport_keeps_gallery_until_all_replacement_photos_exist(
        self, tmp_path, uow
    ):
        workbook = read_eti_workbook(write_workbook(tmp_path / "eti.xlsx"))
        original_urls = {
            (
                photo.sku,
                photo.position,
            ): f"https://cdn.example/old-{photo.position}.webp"
            for photos in workbook.photos.values()
            for photo in photos
        }
        await import_eti_workbook(
            uow.session, workbook, media_urls=original_urls, dry_run=False
        )
        product_id = (
            await uow.session.execute(
                select(Product.id).where(Product.sku == "ETI-TEST-1")
            )
        ).scalar_one()

        async def saved_gallery() -> list[str]:
            return list(
                (
                    await uow.session.execute(
                        select(ProductMedia.url)
                        .where(ProductMedia.product_id == product_id)
                        .order_by(ProductMedia.position)
                    )
                )
                .scalars()
                .all()
            )

        async def saved_primary() -> str | None:
            return (
                await uow.session.execute(
                    select(Product.image_url).where(Product.id == product_id)
                )
            ).scalar_one()

        for retry_workbook, incomplete_urls in (
            (workbook, {}),
            (workbook, {("ETI-TEST-1", 0): "https://cdn.example/new-0.webp"}),
            (replace(workbook, photos={}), original_urls),
        ):
            outcome = await import_eti_workbook(
                uow.session, retry_workbook, media_urls=incomplete_urls, dry_run=False
            )
            assert outcome.media_attached == 0
            assert await saved_gallery() == list(original_urls.values())
            assert await saved_primary() == original_urls[("ETI-TEST-1", 0)]

        replacement_urls = {
            key: value.replace("old", "new") for key, value in original_urls.items()
        }
        outcome = await import_eti_workbook(
            uow.session, workbook, media_urls=replacement_urls, dry_run=False
        )
        assert outcome.media_attached == 2
        assert await saved_gallery() == list(replacement_urls.values())
        assert await saved_primary() == replacement_urls[("ETI-TEST-1", 0)]

    async def test_imports_enext_primary_specs_and_all_photos(self, tmp_path, uow):
        brand_existed = (
            await uow.session.execute(select(Brand.id).where(Brand.name == "E.Next"))
        ).scalar_one_or_none() is not None
        workbook = read_enext_workbook(write_enext_workbook(tmp_path / "enext.xlsx"))
        config = BunnyS3Config(
            endpoint="https://de-s3.storage.bunnycdn.com",
            storage_zone="izihata-product-media",
            password="test-password",
            public_base_url="https://izihata-product-media.b-cdn.net",
        )

        try:
            outcome = await import_eti_workbook(
                uow.session,
                workbook,
                media_urls=planned_media_urls(workbook, config),
                dry_run=False,
                brand_name="E.Next",
                manufacturer_name="e.next",
            )

            product = (
                await uow.session.execute(
                    select(Product)
                    .where(Product.sku == "ENEXT-TEST-1")
                    .options(
                        selectinload(Product.attributes),
                        selectinload(Product.media),
                        selectinload(Product.category),
                    )
                )
            ).scalar_one()
            assert (outcome.created, outcome.updated) == (1, 0)
            assert product.name == "Автоматичний вимикач тестовий"
            assert product.brand == "E.Next"
            assert product.price == Decimal("120.5")
            assert [(item.key, item.value) for item in product.attributes] == [
                ("Код виробника", "ENEXT-TEST-1"),
                ("Виробник", "e.next"),
                ("Опис", "Технічна характеристика " + "x" * 350),
            ]
            assert all(
                item.source == ProductAttributeSource.PRIMARY
                for item in product.attributes
            )
            assert [item.url for item in product.media] == [
                "https://izihata-product-media.b-cdn.net/products/enext/ENEXT-TEST-1/1.webp",
                "https://izihata-product-media.b-cdn.net/products/enext/ENEXT-TEST-1/2.webp",
            ]
            assert product.image_url == product.media[0].url
        finally:
            await uow.session.execute(
                delete(Product).where(Product.sku == "ENEXT-TEST-1")
            )
            if not brand_existed:
                await uow.session.execute(delete(Brand).where(Brand.name == "E.Next"))
            await uow.commit()

    async def test_imports_acko_long_primary_specs_and_typed_media(self, tmp_path, uow):
        brand_existed = (
            await uow.session.execute(select(Brand.id).where(Brand.name == "ACKO"))
        ).scalar_one_or_none() is not None
        workbook = read_acko_workbook(write_acko_workbook(tmp_path / "acko.xlsx"))
        config = BunnyS3Config(
            endpoint="https://de-s3.storage.bunnycdn.com",
            storage_zone="izihata-product-media",
            password="test-password",
            public_base_url="https://izihata-product-media.b-cdn.net",
        )

        try:
            outcome = await import_eti_workbook(
                uow.session,
                workbook,
                media_urls=planned_media_urls(workbook, config),
                dry_run=False,
                brand_name="ACKO",
                manufacturer_name="Аско-Укрем",
            )

            product = (
                await uow.session.execute(
                    select(Product)
                    .where(Product.sku == "ACKO-TEST-1")
                    .options(
                        selectinload(Product.attributes),
                        selectinload(Product.media),
                        selectinload(Product.category),
                    )
                )
            ).scalar_one()
            assert (outcome.created, outcome.updated) == (1, 0)
            assert outcome.primary_specifications == 5
            assert outcome.media_attached == 2
            assert product.sku == "ACKO-TEST-1"
            assert product.name == "Автоматичний вимикач ACKO"
            assert product.brand == "ACKO"
            assert product.price == Decimal("123.45")
            assert product.category.slug == "lowvoltage"
            assert [(item.key, item.value) for item in product.attributes] == [
                ("Код виробника", "ACKO-TEST-1"),
                ("Виробник", "Аско-Укрем"),
                ("Особливості", "x" * 767),
                ("Об'єм", "0,00014"),
                ("Набір матриць", "162535507095120150185240300400"),
            ]
            assert all(
                item.source == ProductAttributeSource.PRIMARY
                for item in product.attributes
            )
            assert product.attributes[-2].numeric_value == Decimal("0.00014")
            assert product.attributes[-2].key == "Об'єм"
            assert product.attributes[-1].numeric_value is None
            assert [media.url for media in product.media] == [
                "https://izihata-product-media.b-cdn.net/products/acko/ACKO-TEST-1/1.jpeg",
                "https://izihata-product-media.b-cdn.net/products/acko/ACKO-TEST-1/2.png",
            ]
            assert [media.alt for media in product.media] == [
                "Автоматичний вимикач ACKO — фото 1",
                "Автоматичний вимикач ACKO — схема 2",
            ]
            assert product.image_url == product.media[0].url
        finally:
            await uow.session.execute(
                delete(Product).where(Product.sku == "ACKO-TEST-1")
            )
            if not brand_existed:
                await uow.session.execute(delete(Brand).where(Brand.name == "ACKO"))
            await uow.commit()

    async def test_acko_sku_conflicts_keep_source_code_and_existing_product(
        self, tmp_path, uow
    ):
        brand_existed = (
            await uow.session.execute(select(Brand.id).where(Brand.name == "ACKO"))
        ).scalar_one_or_none() is not None
        category_id = (
            await uow.session.execute(
                select(Category.id).where(Category.slug == "lowvoltage")
            )
        ).scalar_one()
        original = Product(
            category_id=category_id,
            sku="ACKO-TEST-1",
            slug="acko-existing-hager-test",
            name="Existing Hager product",
            brand="Hager",
            price=Decimal("10.00"),
            stock_status=StockStatus.IN_STOCK,
            stock_quantity=2,
            position=0,
            is_active=True,
        )
        uow.session.add(original)
        await uow.commit()
        workbook = read_acko_workbook(write_acko_workbook(tmp_path / "acko.xlsx"))

        try:
            outcome = await import_eti_workbook(
                uow.session,
                workbook,
                dry_run=False,
                brand_name="ACKO",
                manufacturer_name="Аско-Укрем",
                sku_prefix_for_conflicts="ACKO",
            )

            imported = (
                await uow.session.execute(
                    select(Product)
                    .where(Product.sku == "ACKO-ACKO-TEST-1")
                    .options(selectinload(Product.attributes))
                )
            ).scalar_one()
            preserved = await uow.session.get(Product, original.id)
            assert (outcome.created, outcome.updated) == (1, 0)
            assert outcome.sku_conflicts == [("ACKO-TEST-1", "ACKO-ACKO-TEST-1")]
            assert imported.brand == "ACKO"
            assert imported.sku == "ACKO-ACKO-TEST-1"
            assert imported.attributes[0].key == "Код виробника"
            assert imported.attributes[0].value == "ACKO-TEST-1"
            assert preserved is not None
            assert (preserved.brand, preserved.name, preserved.price) == (
                "Hager",
                "Existing Hager product",
                Decimal("10.00"),
            )

            repeated = await import_eti_workbook(
                uow.session,
                workbook,
                dry_run=False,
                brand_name="ACKO",
                manufacturer_name="Аско-Укрем",
                sku_prefix_for_conflicts="ACKO",
            )
            assert (repeated.created, repeated.updated) == (0, 1)
        finally:
            await uow.session.execute(
                delete(Product).where(
                    Product.sku.in_({"ACKO-TEST-1", "ACKO-ACKO-TEST-1"})
                )
            )
            if not brand_existed:
                await uow.session.execute(delete(Brand).where(Brand.name == "ACKO"))
            await uow.commit()
