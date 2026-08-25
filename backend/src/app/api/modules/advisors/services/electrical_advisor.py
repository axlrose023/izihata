from decimal import ROUND_UP, Decimal

from app.api.modules.advisors.enums import ConductorMaterial, LoadType
from app.api.modules.advisors.schema import (
    AutonomyRequest,
    AutonomyResponse,
    BreakerRequest,
    BreakerResponse,
    CableSizeRequest,
    CableSizeResponse,
    LedPowerSupplyRequest,
    LedPowerSupplyResponse,
)
from app.api.modules.catalog.schema import ProductResponse
from app.database.uow import UnitOfWork

_CABLE_CAPACITY_A: dict[ConductorMaterial, tuple[tuple[Decimal, Decimal], ...]] = {
    ConductorMaterial.COPPER: (
        (Decimal("0.75"), Decimal("10")),
        (Decimal("1.5"), Decimal("16")),
        (Decimal("2.5"), Decimal("25")),
        (Decimal("4"), Decimal("32")),
        (Decimal("6"), Decimal("40")),
        (Decimal("10"), Decimal("63")),
        (Decimal("16"), Decimal("80")),
    ),
    ConductorMaterial.ALUMINUM: (
        (Decimal("2.5"), Decimal("19")),
        (Decimal("4"), Decimal("25")),
        (Decimal("6"), Decimal("32")),
        (Decimal("10"), Decimal("50")),
        (Decimal("16"), Decimal("63")),
        (Decimal("25"), Decimal("80")),
    ),
}
_BREAKER_NOMINALS = (6, 10, 16, 20, 25, 32, 40, 50, 63)
_REFERENCE_NOTICE = (
    "Reference calculation only. Verify cable route, ambient conditions, "
    "short-circuit protection, and local standards with a qualified electrician."
)


class ElectricalAdvisorService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def calculate_cable(self, request: CableSizeRequest) -> CableSizeResponse:
        current = request.calculated_current_a
        length_factor = Decimal("1") + max(request.length_m - 30, Decimal("0")) / 300
        design_current = current * length_factor
        cross_section = self._select_cross_section(
            request.conductor_material,
            design_current,
        )
        products = await self._uow.products.list_by_attribute(
            category_slug="cable",
            key="Переріз",
            values={self._cross_section_label(cross_section)},
        )
        return CableSizeResponse(
            current_a=self._round(current),
            recommended_cross_section_mm2=cross_section,
            reference_notice=_REFERENCE_NOTICE,
            products=[ProductResponse.from_product(product) for product in products],
        )

    async def calculate_breaker(self, request: BreakerRequest) -> BreakerResponse:
        current = request.calculated_current_a
        multiplier = (
            Decimal("1.25") if request.load_type == LoadType.MOTOR else Decimal("1.1")
        )
        target_current = current * multiplier
        nominal = next(
            (value for value in _BREAKER_NOMINALS if Decimal(value) >= target_current),
            None,
        )
        requires_specialist = nominal is None
        if (
            nominal is not None
            and request.wiring_current_limit_a is not None
            and Decimal(nominal) > request.wiring_current_limit_a
        ):
            nominal = None
            requires_specialist = True
        curve = "C" if request.load_type == LoadType.MOTOR else "B"
        products = []
        if nominal is not None:
            products = list(
                await self._uow.products.list_by_attribute(
                    category_slug="lowvoltage",
                    key="Номінал",
                    values={f"{nominal} А"},  # noqa: RUF001
                )
            )
        return BreakerResponse(
            current_a=self._round(current),
            recommended_nominal_a=nominal,
            recommended_curve=curve,
            requires_specialist=requires_specialist,
            reference_notice=_REFERENCE_NOTICE,
            products=[ProductResponse.from_product(product) for product in products],
        )

    async def calculate_led_power_supply(
        self,
        request: LedPowerSupplyRequest,
    ) -> LedPowerSupplyResponse:
        load = request.length_m * request.watts_per_meter
        recommended = load * (Decimal("1") + Decimal(request.reserve_percent) / 100)
        products = await self._uow.products.list_by_category("power")
        return LedPowerSupplyResponse(
            load_w=self._round(load),
            recommended_power_w=self._round(recommended),
            reference_notice=_REFERENCE_NOTICE,
            products=[ProductResponse.from_product(product) for product in products],
        )

    async def calculate_autonomy(self, request: AutonomyRequest) -> AutonomyResponse:
        energy = request.load_w * request.hours
        capacity = energy / (
            request.battery_voltage_v
            * request.inverter_efficiency
            * request.discharge_depth
        )
        inverter_power = request.load_w * Decimal("1.25")
        products = await self._uow.products.list_by_category("power")
        return AutonomyResponse(
            required_energy_wh=self._round(energy),
            recommended_battery_capacity_ah=self._round(capacity),
            recommended_inverter_power_w=self._round(inverter_power),
            reference_notice=_REFERENCE_NOTICE,
            products=[ProductResponse.from_product(product) for product in products],
        )

    @staticmethod
    def _select_cross_section(
        material: ConductorMaterial,
        design_current: Decimal,
    ) -> Decimal:
        for cross_section, capacity in _CABLE_CAPACITY_A[material]:
            if capacity >= design_current:
                return cross_section
        return _CABLE_CAPACITY_A[material][-1][0]

    @staticmethod
    def _cross_section_label(cross_section: Decimal) -> str:
        return (
            f"{cross_section:.1f} мм²" if cross_section < 10 else f"{cross_section} мм²"
        )

    @staticmethod
    def _round(value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"), rounding=ROUND_UP)
