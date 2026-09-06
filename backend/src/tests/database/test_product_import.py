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


@pytest.mark.asyncio
class TestPlaceholderPricing:
    """A stock file with no prices still has to be loadable — but never visible."""

    @pytest_asyncio.fixture(autouse=True)
    async def _clean_slate(self, uow):
        async def purge() -> None:
            await uow.session.execute(delete(Product).where(Product.sku.like("PLC-%")))
            await uow.commit()

        await purge()
        yield
        await purge()

    @staticmethod
    def _rows() -> list[ImportRow]:
        return [ImportRow("PLC-1", "Авт. вимикач ETIMAT 6 1p C16", None, 5)]

    async def test_without_a_placeholder_the_row_is_skipped(self, uow):
        outcome = await import_products(
            uow.session, self._rows(), brand="ETI", dry_run=False
        )

        assert outcome.created == 0
        assert outcome.skipped_without_price == ["PLC-1"]

    async def test_placeholder_imports_the_row_hidden(self, uow):
        outcome = await import_products(
            uow.session,
            self._rows(),
            brand="ETI",
            placeholder_price=Decimal("0.01"),
            dry_run=False,
        )

        assert (outcome.created, outcome.needs_pricing) == (1, 1)
        product = (
            await uow.session.execute(select(Product).where(Product.sku == "PLC-1"))
        ).scalar_one()
        assert product.price == Decimal("0.01")
        assert product.is_active is False

    async def test_placeholder_rows_stay_hidden_even_with_activate(self, uow):
        await import_products(
            uow.session,
            self._rows(),
            brand="ETI",
            placeholder_price=Decimal("0.01"),
            activate=True,
            dry_run=False,
        )

        product = (
            await uow.session.execute(select(Product).where(Product.sku == "PLC-1"))
        ).scalar_one()
        assert product.is_active is False

    async def test_a_placeholder_never_overwrites_a_real_price(self, uow):
        await import_products(
            uow.session,
            self._rows(),
            brand="ETI",
            placeholder_price=Decimal("0.01"),
            dry_run=False,
        )
        product = (
            await uow.session.execute(select(Product).where(Product.sku == "PLC-1"))
        ).scalar_one()
        product.price = Decimal("249.00")
        await uow.commit()

        await import_products(
            uow.session,
            self._rows(),
            brand="ETI",
            placeholder_price=Decimal("0.01"),
            dry_run=False,
        )

        refreshed = (
            await uow.session.execute(select(Product).where(Product.sku == "PLC-1"))
        ).scalar_one()
        assert refreshed.price == Decimal("249.00")


@pytest.mark.asyncio
class TestCategoryRemapping:
    """Fixed rules have to be able to reach products that are already imported."""

    @pytest_asyncio.fixture(autouse=True)
    async def _clean_slate(self, uow):
        async def purge() -> None:
            await uow.session.execute(delete(Product).where(Product.sku.like("RMP-%")))
            await uow.commit()

        await purge()
        yield
        await purge()

    @staticmethod
    def _rows() -> list[ImportRow]:
        return [ImportRow("RMP-1", "Авт. вимикач ETIMAT 6 1p C16", Decimal("10.00"), 1)]

    async def _misplace(self, uow) -> Product:
        await import_products(uow.session, self._rows(), brand="ETI", dry_run=False)
        product = (
            await uow.session.execute(select(Product).where(Product.sku == "RMP-1"))
        ).scalar_one()
        wrong = (
            await uow.session.execute(select(Category).where(Category.slug == "light"))
        ).scalar_one()
        product.category_id = wrong.id
        await uow.commit()
        return product

    async def test_categories_are_left_alone_by_default(self, uow):
        product = await self._misplace(uow)
        moved_to = product.category_id

        outcome = await import_products(
            uow.session, self._rows(), brand="ETI", dry_run=False
        )

        assert outcome.recategorised == 0
        refreshed = (
            await uow.session.execute(select(Product).where(Product.sku == "RMP-1"))
        ).scalar_one()
        assert refreshed.category_id == moved_to

    async def test_remap_restores_the_rule_based_category(self, uow):
        await self._misplace(uow)

        outcome = await import_products(
            uow.session,
            self._rows(),
            brand="ETI",
            remap_categories=True,
            dry_run=False,
        )

        assert outcome.recategorised == 1
        refreshed = (
            await uow.session.execute(select(Product).where(Product.sku == "RMP-1"))
        ).scalar_one()
        category = (
            await uow.session.execute(
                select(Category).where(Category.id == refreshed.category_id)
            )
        ).scalar_one()
        assert category.slug == "lowvoltage"
        assert refreshed.subcategory_id is not None

    async def test_remap_is_a_no_op_when_the_category_already_matches(self, uow):
        await import_products(uow.session, self._rows(), brand="ETI", dry_run=False)

        outcome = await import_products(
            uow.session,
            self._rows(),
            brand="ETI",
            remap_categories=True,
            dry_run=False,
        )

        assert outcome.recategorised == 0


class TestRuleCorrections:
    """Families that were mapped wrong in the first import."""

    @pytest.mark.parametrize(
        ("name", "category", "subcategory"),
        [
            (
                "Реле диференційне (ПЗВ) 2р EFI-P2 16/0,03 тип AC (10kA)",
                "lowvoltage",
                "ПЗВ (УЗО)",
            ),
            (
                "Повітр. авт. вим. викочувальний EPL-08 3H AD/M2C2S2",
                "lowvoltage",
                "Автоматичні вимикачі (модульні / корпусні / повітряні)",
            ),
            ("Короб перфорований B 25x40 T (ПВХ, Ш25xВ40, 2м)", "cabletrays", None),
            ("Сальник M20 (еластичний, Ø8-13мм, IP67)", "installation", None),
            ("Кабельний ввід M-50G (Ø20..37мм, IP68)", "installation", None),
        ],
    )
    def test_family_lands_in_the_right_place(
        self, name: str, category: str, subcategory: str | None
    ):
        mapped, sub, matched = classify(name)

        assert (mapped, sub, matched) == (category, subcategory, True)

    def test_a_plain_relay_is_still_a_relay(self):
        assert classify("Реле контролю фаз")[0] == "relay"

    def test_frequency_drives_have_no_home_yet(self):
        assert classify("Перетворювач частоти CFW500 D 24P0")[0] == FALLBACK_CATEGORY


@pytest.mark.asyncio
class TestPublishingOnPriceArrival:
    """When the real price list lands, stubs should go live without hand work."""

    @pytest_asyncio.fixture(autouse=True)
    async def _clean_slate(self, uow):
        async def purge() -> None:
            await uow.session.execute(delete(Product).where(Product.sku.like("PUB-%")))
            await uow.commit()

        await purge()
        yield
        await purge()

    @staticmethod
    def _stock_only() -> list[ImportRow]:
        return [
            ImportRow("PUB-1", "Авт. вимикач ETIMAT 6 1p C16", None, 4),
            ImportRow("PUB-2", "Щось геть невідоме", None, 4),
        ]

    @staticmethod
    def _priced() -> list[ImportRow]:
        return [
            ImportRow("PUB-1", "Авт. вимикач ETIMAT 6 1p C16", Decimal("156.00"), 4),
            ImportRow("PUB-2", "Щось геть невідоме", Decimal("99.00"), 4),
        ]

    async def _load_stubs(self, uow) -> None:
        await import_products(
            uow.session,
            self._stock_only(),
            brand="ETI",
            placeholder_price=Decimal("0.01"),
            dry_run=False,
        )

    async def _by_sku(self, uow, sku: str) -> Product:
        return (
            await uow.session.execute(select(Product).where(Product.sku == sku))
        ).scalar_one()

    async def test_real_price_publishes_the_stub(self, uow):
        await self._load_stubs(uow)

        outcome = await import_products(
            uow.session,
            self._priced(),
            brand="ETI",
            placeholder_price=Decimal("0.01"),
            activate=True,
            dry_run=False,
        )

        assert outcome.published == 1
        product = await self._by_sku(uow, "PUB-1")
        assert product.price == Decimal("156.00")
        assert product.is_active is True

    async def test_unmapped_products_stay_hidden_even_when_priced(self, uow):
        await self._load_stubs(uow)

        await import_products(
            uow.session,
            self._priced(),
            brand="ETI",
            placeholder_price=Decimal("0.01"),
            activate=True,
            dry_run=False,
        )

        product = await self._by_sku(uow, "PUB-2")
        assert product.price == Decimal("99.00")
        assert product.is_active is False

    async def test_a_product_staff_hid_on_purpose_is_not_resurrected(self, uow):
        await self._load_stubs(uow)
        await import_products(
            uow.session,
            self._priced(),
            brand="ETI",
            placeholder_price=Decimal("0.01"),
            activate=True,
            dry_run=False,
        )
        product = await self._by_sku(uow, "PUB-1")
        product.is_active = False
        await uow.commit()

        outcome = await import_products(
            uow.session,
            self._priced(),
            brand="ETI",
            placeholder_price=Decimal("0.01"),
            activate=True,
            dry_run=False,
        )

        assert outcome.published == 0
        assert (await self._by_sku(uow, "PUB-1")).is_active is False

    async def test_nothing_is_published_without_the_flag(self, uow):
        await self._load_stubs(uow)

        outcome = await import_products(
            uow.session,
            self._priced(),
            brand="ETI",
            placeholder_price=Decimal("0.01"),
            dry_run=False,
        )

        assert outcome.published == 0
        assert (await self._by_sku(uow, "PUB-1")).is_active is False


class TestKeywordFallbackRules:
    """Ukrainian names often lead with an adjective, so the noun can be second."""

    @pytest.mark.parametrize(
        ("name", "category"),
        [
            ("Багатофункціональне реле (таблетка) SMR-T", "relay"),
            ("Програмоване реле CLW-02 12HR-D 3RD", "relay"),
            ("Сутінкове реле SOU-1 230V AC", "relay"),
            ("Термодатчик TC-0 (0...+70)", "relay"),
            ("Лічильник 3-фазн. DEC-2 CT (6А, з ТС)", "metering"),
            ("Аналізатор мережі ENA3 (144x144мм)", "metering"),
            ("Акумуляторна батарея HD12-120 SOC", "power"),
            ("Інвертор гібридний TAB (3-фазн., 8,0кВт)", "power"),
            ("Металевий щит внутрішнього монтажу 4XP160", "panels"),
            ("Механічне блокування BECO", "lowvoltage"),
            ("Марковання клем самоклеюче ES-TAP1640AW", "installation"),
        ],
    )
    def test_keyword_anywhere_in_the_name_is_enough(self, name: str, category: str):
        mapped, _, matched = classify(name)

        assert (mapped, matched) == (category, True)

    @pytest.mark.parametrize(
        ("name", "category"),
        [
            # The leading-name rules must keep winning over the keyword pass.
            ("Реле диференційне (ПЗВ) 2р EFI-P2 16/0,03", "lowvoltage"),
            ("Авт. вимикач ETIMAT 6 1p C16", "lowvoltage"),
            ("Щит зовнішн. розподільний ECT 18PT", "panels"),
            ("Лампа сигнальна LED матова ECLI-16", "switching"),
            ("Короб перфорований B 25x40 T", "cabletrays"),
        ],
    )
    def test_leading_rules_still_take_precedence(self, name: str, category: str):
        assert classify(name)[0] == category

    def test_a_name_that_is_only_a_model_code_stays_unmapped(self):
        assert classify("M-12N (Гайка для M-12G, ГК-16)")[2] is False


@pytest.mark.asyncio
class TestPublishingOnClassification:
    """A product parked in the fallback goes live once the rules can place it."""

    @pytest_asyncio.fixture(autouse=True)
    async def _clean_slate(self, uow):
        async def purge() -> None:
            await uow.session.execute(delete(Product).where(Product.sku.like("CLS-%")))
            await uow.commit()

        await purge()
        yield
        await purge()

    @staticmethod
    def _rows(name: str) -> list[ImportRow]:
        return [ImportRow("CLS-1", name, Decimal("120.00"), 3)]

    async def _by_sku(self, uow) -> Product:
        return (
            await uow.session.execute(select(Product).where(Product.sku == "CLS-1"))
        ).scalar_one()

    async def test_priced_but_unclassified_products_stay_hidden(self, uow):
        outcome = await import_products(
            uow.session,
            self._rows("Щось геть невідоме"),
            brand="ETI",
            activate=True,
            dry_run=False,
        )

        assert outcome.published == 0
        assert (await self._by_sku(uow)).is_active is False

    async def test_leaving_the_fallback_publishes_the_product(self, uow):
        await import_products(
            uow.session,
            self._rows("Щось геть невідоме"),
            brand="ETI",
            activate=True,
            dry_run=False,
        )

        # The same SKU, now under a name the rules understand.
        outcome = await import_products(
            uow.session,
            self._rows("Авт. вимикач ETIMAT 6 1p C16"),
            brand="ETI",
            activate=True,
            remap_categories=True,
            dry_run=False,
        )

        assert outcome.published == 1
        product = await self._by_sku(uow)
        assert product.is_active is True

    async def test_nothing_is_published_without_remapping(self, uow):
        await import_products(
            uow.session,
            self._rows("Щось геть невідоме"),
            brand="ETI",
            activate=True,
            dry_run=False,
        )

        outcome = await import_products(
            uow.session,
            self._rows("Авт. вимикач ETIMAT 6 1p C16"),
            brand="ETI",
            activate=True,
            dry_run=False,
        )

        assert outcome.published == 0
        assert (await self._by_sku(uow)).is_active is False

    async def test_a_classified_product_hidden_by_staff_is_not_resurrected(self, uow):
        await import_products(
            uow.session,
            self._rows("Авт. вимикач ETIMAT 6 1p C16"),
            brand="ETI",
            activate=True,
            dry_run=False,
        )
        product = await self._by_sku(uow)
        product.is_active = False
        await uow.commit()

        outcome = await import_products(
            uow.session,
            self._rows("Авт. вимикач ETIMAT 6 1p C16"),
            brand="ETI",
            activate=True,
            remap_categories=True,
            dry_run=False,
        )

        assert outcome.published == 0
        assert (await self._by_sku(uow)).is_active is False
