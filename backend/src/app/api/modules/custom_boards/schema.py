from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator

from app.api.common.schema import PaginationParams, StrictSchema
from app.api.common.utils import (
    normalize_email,
    normalize_optional_text,
    normalize_phone,
    normalize_resource_url,
    normalize_text,
)
from app.api.modules.custom_boards.enums import BoardApplication, BoardRequestStatus
from app.api.modules.custom_boards.models import (
    CustomBoardPortfolioItem,
    CustomBoardRequest,
)


class BoardEstimateRequest(StrictSchema):
    application: BoardApplication
    groups_count: int = Field(ge=1, le=200)
    ip_class: str = Field(min_length=2, max_length=16, pattern=r"^IP\d{2}$")
    automation_brand: str | None = Field(default=None, max_length=120)
    budget: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)

    @field_validator("ip_class", mode="before")
    @classmethod
    def normalize_ip_class(cls, value: object) -> str:
        return normalize_text(value).upper()

    @field_validator("automation_brand", mode="before")
    @classmethod
    def normalize_brand(cls, value: object | None) -> str | None:
        return normalize_optional_text(value)


class BoardEstimateResponse(StrictSchema):
    starting_price: Decimal
    response_sla_hours: int
    suggested_components: list[str]
    reference_notice: str


class CreateCustomBoardRequest(BoardEstimateRequest):
    customer_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=8, max_length=24)
    email: str | None = Field(default=None, max_length=254)
    details: str | None = Field(default=None, max_length=4000)

    @field_validator("customer_name", "details", mode="before")
    @classmethod
    def normalize_text_fields(cls, value: object | None) -> str | None:
        return normalize_optional_text(value)

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, value: object) -> str:
        return normalize_phone(value)

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, value: object | None) -> str | None:
        return normalize_email(value) if value is not None else None


class CustomBoardRequestResponse(StrictSchema):
    id: UUID
    status: BoardRequestStatus
    starting_price: Decimal
    response_sla_hours: int


class AdminCustomBoardRequestResponse(StrictSchema):
    id: UUID
    customer_name: str
    phone: str
    email: str | None
    application: BoardApplication
    groups_count: int
    ip_class: str
    automation_brand: str | None
    budget: Decimal | None
    details: str | None
    estimated_from_price: Decimal
    status: BoardRequestStatus
    created_at: datetime

    @classmethod
    def from_request(
        cls, request: CustomBoardRequest
    ) -> "AdminCustomBoardRequestResponse":
        return cls.model_validate(request)

    model_config = ConfigDict(extra="forbid", from_attributes=True)


class CustomBoardRequestListParams(PaginationParams):
    status: BoardRequestStatus | None = None


class CustomBoardRequestListResponse(StrictSchema):
    items: list[AdminCustomBoardRequestResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class UpdateCustomBoardRequestStatus(StrictSchema):
    status: BoardRequestStatus


class PortfolioItemResponse(StrictSchema):
    id: UUID
    title: str
    description: str
    image_url: str
    position: int

    @classmethod
    def from_item(cls, item: CustomBoardPortfolioItem) -> "PortfolioItemResponse":
        return cls.model_validate(item)

    model_config = ConfigDict(extra="forbid", from_attributes=True)


class CreatePortfolioItemRequest(StrictSchema):
    title: str = Field(min_length=2, max_length=240)
    description: str = Field(min_length=2, max_length=4000)
    image_url: str = Field(min_length=1, max_length=500)
    position: int = Field(default=0, ge=0, le=1000)

    @field_validator("title", "description", mode="before")
    @classmethod
    def normalize_text_fields(cls, value: object) -> str:
        return normalize_text(value)

    @field_validator("image_url", mode="before")
    @classmethod
    def validate_image_url(cls, value: object) -> str:
        normalized = normalize_resource_url(value)
        if normalized is None:
            raise ValueError("Image URL is required")
        return normalized


class UpdatePortfolioItemRequest(StrictSchema):
    title: str | None = Field(default=None, min_length=2, max_length=240)
    description: str | None = Field(default=None, min_length=2, max_length=4000)
    image_url: str | None = Field(default=None, max_length=500)
    position: int | None = Field(default=None, ge=0, le=1000)
    is_active: bool | None = None

    @field_validator("title", "description", mode="before")
    @classmethod
    def normalize_text_fields(cls, value: object | None) -> str | None:
        return normalize_optional_text(value)

    @field_validator("image_url", mode="before")
    @classmethod
    def validate_image_url(cls, value: object | None) -> str | None:
        return normalize_resource_url(value)
