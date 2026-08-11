import datetime
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.api.common.schema import PaginationParams, StrictSchema
from app.api.common.utils import (
    normalize_optional_text,
    normalize_phone,
    normalize_text,
)
from app.api.modules.leads.enums import LeadStatus, LeadType


class CreateLeadRequest(StrictSchema):
    type: LeadType
    name: str = Field(min_length=2, max_length=120)
    phone: str
    company: str | None = Field(default=None, min_length=2, max_length=180)
    product_id: UUID | None = None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> str:
        return normalize_text(value)

    @field_validator("company", mode="before")
    @classmethod
    def normalize_company(cls, value: object | None) -> str | None:
        return normalize_optional_text(value)

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone_number(cls, value: object) -> str:
        return normalize_phone(value)

    @model_validator(mode="after")
    def validate_context(self) -> "CreateLeadRequest":
        if self.type == LeadType.QUICK_BUY and self.product_id is None:
            raise ValueError("product_id is required for quick_buy lead")
        if self.type == LeadType.WHOLESALE and not self.company:
            raise ValueError("company is required for wholesale lead")
        if self.type == LeadType.CALLBACK and self.product_id is not None:
            raise ValueError("product_id is not accepted for callback lead")
        return self


class LeadResponse(StrictSchema):
    id: UUID
    type: LeadType
    status: LeadStatus
    created_at: datetime.datetime


class AdminLeadResponse(LeadResponse):
    name: str
    phone: str
    company: str | None
    product_id: UUID | None


class LeadListParams(PaginationParams):
    status: LeadStatus | None = None
    type: LeadType | None = None


class LeadListResponse(StrictSchema):
    items: list[AdminLeadResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class UpdateLeadStatusRequest(StrictSchema):
    status: LeadStatus
