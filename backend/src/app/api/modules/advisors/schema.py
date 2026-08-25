from decimal import Decimal

from pydantic import Field, model_validator

from app.api.common.schema import StrictSchema
from app.api.modules.advisors.enums import ConductorMaterial, LoadType
from app.api.modules.catalog.schema import ProductResponse


class ElectricalLoadRequest(StrictSchema):
    power_w: Decimal | None = Field(default=None, gt=0, le=1000000)
    current_a: Decimal | None = Field(default=None, gt=0, le=10000)
    voltage_v: Decimal = Field(default=Decimal("230"), gt=0, le=1000)

    @model_validator(mode="after")
    def require_single_load_value(self) -> "ElectricalLoadRequest":
        if (self.power_w is None) == (self.current_a is None):
            raise ValueError("Exactly one of power_w or current_a must be provided")
        return self

    @property
    def calculated_current_a(self) -> Decimal:
        if self.current_a is not None:
            return self.current_a
        if self.power_w is None:
            raise RuntimeError("Validated electrical load has no power value")
        return self.power_w / self.voltage_v


class CableSizeRequest(ElectricalLoadRequest):
    length_m: Decimal = Field(gt=0, le=10000)
    conductor_material: ConductorMaterial = ConductorMaterial.COPPER


class CableSizeResponse(StrictSchema):
    current_a: Decimal
    recommended_cross_section_mm2: Decimal
    reference_notice: str
    products: list[ProductResponse]


class BreakerRequest(ElectricalLoadRequest):
    load_type: LoadType = LoadType.RESISTIVE
    wiring_current_limit_a: Decimal | None = Field(default=None, gt=0, le=10000)


class BreakerResponse(StrictSchema):
    current_a: Decimal
    recommended_nominal_a: int | None
    recommended_curve: str
    requires_specialist: bool
    reference_notice: str
    products: list[ProductResponse]


class LedPowerSupplyRequest(StrictSchema):
    length_m: Decimal = Field(gt=0, le=10000)
    watts_per_meter: Decimal = Field(gt=0, le=10000)
    reserve_percent: int = Field(default=20, ge=10, le=50)


class LedPowerSupplyResponse(StrictSchema):
    load_w: Decimal
    recommended_power_w: Decimal
    reference_notice: str
    products: list[ProductResponse]


class AutonomyRequest(StrictSchema):
    load_w: Decimal = Field(gt=0, le=1000000)
    hours: Decimal = Field(gt=0, le=240)
    battery_voltage_v: Decimal = Field(gt=0, le=1000)
    inverter_efficiency: Decimal = Field(default=Decimal("0.85"), gt=0, le=1)
    discharge_depth: Decimal = Field(default=Decimal("0.80"), gt=0, le=1)


class AutonomyResponse(StrictSchema):
    required_energy_wh: Decimal
    recommended_battery_capacity_ah: Decimal
    recommended_inverter_power_w: Decimal
    reference_notice: str
    products: list[ProductResponse]
