from enum import StrEnum


class ConductorMaterial(StrEnum):
    COPPER = "copper"
    ALUMINUM = "aluminum"


class LoadType(StrEnum):
    RESISTIVE = "resistive"
    LIGHTING = "lighting"
    MOTOR = "motor"
