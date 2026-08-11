from enum import StrEnum


class LeadType(StrEnum):
    CALLBACK = "callback"
    QUICK_BUY = "quick_buy"
    WHOLESALE = "wholesale"


class LeadStatus(StrEnum):
    NEW = "new"
    CONTACTED = "contacted"
    CLOSED = "closed"
