from enum import StrEnum


class BoardApplication(StrEnum):
    APARTMENT = "apartment"
    HOUSE = "house"
    INDUSTRIAL = "industrial"


class BoardRequestStatus(StrEnum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    QUOTED = "quoted"
    CLOSED = "closed"
    CANCELLED = "cancelled"
