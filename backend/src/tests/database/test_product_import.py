from decimal import Decimal
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from app.api.modules.catalog.enums import StockStatus
from app.api.modules.catalog.models import Category, Product
from app.database.imports import ImportRow, import_products, read_rows
from app.database.imports.category_rules import FALLBACK_CATEGORY, classify


def write(tmp_path: Path, body: str, name: str = "stock.csv") -> Path:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


class TestReadRows:
    def test_reads_ukrainian_supplier_headers(self, tmp_path: Path):
        path = write(
            tmp_path,
            "Артикул;Найменування;Вільний залишок;Ціна\n"
            "4771600;Лампа сигнальна LED;224;153,40\n",
        )

        rows = read_rows(path)

        assert rows == [
            ImportRow(
                sku="4771600",
                name="Лампа сигнальна LED",
                price=Decimal("153.40"),
                stock=224,
            )
        ]

    def test_reads_english_headers_and_commas(self, tmp_path: Path):
        path = write(tmp_path, "sku,name,stock,price\nA-1,Breaker,5,10.00\n")

        rows = read_rows(path)

        assert rows[0].sku == "A-1"
        assert rows[0].price == Decimal("10.00")
        assert rows[0].stock == 5

    def test_missing_price_column_is_allowed(self, tmp_path: Path):
        path = write(
            tmp_path, "Артикул;Найменування;Вільний залишок\nA-1;Авт. ETIMAT;3\n"
        )

        rows = read_rows(path)

        assert rows[0].price is None

    def test_last_row_wins_for_a_repeated_sku(self, tmp_path: Path):
        path = write(
            tmp_path,
            "sku,name,price\nA-1,First,10.00\nA-1,Second,20.00\n",
        )

        rows = read_rows(path)

        assert len(rows) == 1
        assert rows[0].name == "Second"

    def test_rejects_a_file_without_identifying_columns(self, tmp_path: Path):
        path = write(tmp_path, "залишок;ціна\n5;10\n")

        with pytest.raises(ValueError, match="missing required column"):
            read_rows(path)

    def test_ignores_blank_and_ragged_rows(self, tmp_path: Path):
        path = write(
            tmp_path,
            "sku,name,price\n,Nameless,10\nA-2,,10\nA-3\nA-4,Good,10\n",
        )

        assert [row.sku for row in read_rows(path)] == ["A-4"]


class TestClassify:
    @pytest.mark.parametrize(
        ("name", "category"),
        [
            ("Авт. вимикач ETIMAT 6 1p C16", "lowvoltage"),
            ("Авт.захисту двиг. MSP-25", "lowvoltage"),
            ("Запобіжник CH14x51", "lowvoltage"),
            ("Лампа сигнальна LED матова ECLI", "switching"),
            ("Кнопковий пост 1-модул. ESB1-V2", "switching"),
            ("Щит модульний ECT 12PO", "panels"),
            ("Реле контролю фаз", "relay"),
            ("Розетка силова", "sockets"),
        ],
    )
    def test_maps_known_product_families(self, name: str, category: str):
        mapped, _, matched = classify(name)

        assert (mapped, matched) == (category, True)

    def test_unknown_names_fall_back_and_report_it(self):
        assert classify("Щось невідоме") == (FALLBACK_CATEGORY, None, False)

    def test_motor_protection_wins_over_the_generic_breaker_rule(self):
        _, subcategory, _ = classify("Авт.захисту двиг. MSP-25")

        assert subcategory == "Автомати захисту двигуна"


@pytest.mark.asyncio
class TestImportProducts:
    @pytest_asyncio.fixture(autouse=True)
    async def _clean_slate(self, uow):
        """The suite shares one database, so these products must not outlive the test."""

        async def purge() -> None:
            await uow.session.execute(delete(Product).where(Product.sku.like("IMP-%")))
            await uow.commit()

        await purge()
        yield
        await purge()

    @staticmethod
    def _rows() -> list[ImportRow]:
        return [
            ImportRow("IMP-1", "Авт. вимикач ETIMAT 6 1p C16", Decimal("120.50"), 7),
            ImportRow("IMP-2", "Щось геть невідоме", Decimal("80.00"), 0),
            ImportRow("IMP-3", "Запобіжник CH14x51", None, 4),
        ]

    async def test_dry_run_writes_nothing(self, uow):
        outcome = await import_products(
            uow.session, self._rows(), brand="ETI", dry_run=True
        )

        assert outcome.created == 2
        assert outcome.skipped_without_price == ["IMP-3"]
        stored = (
            (
                await uow.session.execute(
                    select(Product).where(Product.sku.like("IMP-%"))
                )
            )
            .scalars()
            .all()
        )
        assert stored == []

    async def test_apply_creates_products_hidden_by_default(self, uow):
        await import_products(uow.session, self._rows(), brand="ETI", dry_run=False)

        created = {
            product.sku: product
            for product in (
                await uow.session.execute(
                    select(Product).where(Product.sku.like("IMP-%"))
                )
            )
            .scalars()
            .all()
        }
        assert set(created) == {"IMP-1", "IMP-2"}
        assert all(not product.is_active for product in created.values())
        assert created["IMP-1"].brand == "ETI"
        assert created["IMP-1"].price == Decimal("120.50")
        assert created["IMP-1"].stock_status == StockStatus.IN_STOCK
        # No stock left means the storefront must not offer it.
        assert created["IMP-2"].stock_status == StockStatus.OUT_OF_STOCK

    async def test_activate_publishes_only_confidently_mapped_rows(self, uow):
        await import_products(
            uow.session,
            self._rows(),
            brand="ETI",
            activate=True,
            dry_run=False,
        )

        by_sku = {
            product.sku: product
            for product in (
                await uow.session.execute(
                    select(Product).where(Product.sku.like("IMP-%"))
                )
            )
            .scalars()
            .all()
        }
        assert by_sku["IMP-1"].is_active is True
        # Unmapped rows stay hidden even when publishing was requested.
        assert by_sku["IMP-2"].is_active is False

    async def test_rerun_updates_instead_of_duplicating(self, uow):
        await import_products(uow.session, self._rows(), brand="ETI", dry_run=False)
        repriced = [
            ImportRow(
                "IMP-1",
                "Авт. вимикач ETIMAT 6 1p C16 (нова назва)",
                Decimal("131.00"),
                0,
            ),
        ]

        outcome = await import_products(
            uow.session, repriced, brand="ETI", dry_run=False
        )

        assert (outcome.created, outcome.updated) == (0, 1)
        product = (
            await uow.session.execute(select(Product).where(Product.sku == "IMP-1"))
        ).scalar_one()
        assert product.price == Decimal("131.00")
        assert product.name.endswith("(нова назва)")
        assert product.stock_status == StockStatus.OUT_OF_STOCK

    async def test_rerun_keeps_a_category_staff_corrected_by_hand(self, uow):
        await import_products(uow.session, self._rows(), brand="ETI", dry_run=False)
        product = (
            await uow.session.execute(select(Product).where(Product.sku == "IMP-2"))
        ).scalar_one()
        moved_to = (
            await uow.session.execute(select(Category).where(Category.slug == "light"))
        ).scalar_one()
        product.category_id = moved_to.id
        await uow.commit()

        await import_products(uow.session, self._rows(), brand="ETI", dry_run=False)

        refreshed = (
            await uow.session.execute(select(Product).where(Product.sku == "IMP-2"))
        ).scalar_one()
        assert refreshed.category_id == moved_to.id

    async def test_unmapped_rows_land_in_the_fallback_category(self, uow):
        outcome = await import_products(
            uow.session, self._rows(), brand="ETI", dry_run=False
        )

        assert outcome.unmapped == ["IMP-2 Щось геть невідоме"]
        product = (
            await uow.session.execute(select(Product).where(Product.sku == "IMP-2"))
        ).scalar_one()
        category = (
            await uow.session.execute(
                select(Category).where(Category.id == product.category_id)
            )
        ).scalar_one()
        assert category.slug == FALLBACK_CATEGORY
