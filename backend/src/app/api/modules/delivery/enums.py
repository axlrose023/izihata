from enum import StrEnum


class DeliveryPointKind(StrEnum):
    BRANCH = "branch"
    LOCKER = "locker"


LOCKER_TYPE_REFS = {
    "95dc212d-479c-4ffb-a8ab-8c1b9073d0bc",
    "f9316480-5f2d-425d-bc2c-ac7cd29decf0",
}
NOVA_POSHTA_LOCKER_TYPE_REF = "f9316480-5f2d-425d-bc2c-ac7cd29decf0"
