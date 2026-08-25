from enum import StrEnum


class CompanyKind(StrEnum):
    FOP = "fop"
    LEGAL_ENTITY = "legal_entity"


class CompanyStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
