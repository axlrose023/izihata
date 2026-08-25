from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.api.common.schema import PaginationParams, StrictSchema
from app.api.common.utils import (
    normalize_email,
    normalize_optional_text,
    normalize_phone,
    normalize_text,
)
from app.api.modules.customers.enums import CompanyKind, CompanyStatus
from app.api.modules.customers.models import Customer, CustomerCompany


class CustomerRegistrationRequest(StrictSchema):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=72)
    phone: str | None = Field(default=None, max_length=24)

    @field_validator("full_name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> str:
        return normalize_text(value)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email_value(cls, value: object) -> str:
        return normalize_email(value)

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone_value(cls, value: object | None) -> str | None:
        return normalize_phone(value) if value is not None else None


class CustomerLoginRequest(StrictSchema):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=72)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email_value(cls, value: object) -> str:
        return normalize_email(value)


class CustomerCompanyRequest(StrictSchema):
    kind: CompanyKind
    name: str = Field(min_length=2, max_length=180)
    edrpou: str = Field(pattern=r"^\d{8,10}$")

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> str:
        return normalize_text(value)


class CustomerCompanyResponse(StrictSchema):
    id: UUID
    kind: CompanyKind
    name: str
    edrpou: str
    status: CompanyStatus
    manager_name: str | None
    cumulative_discount_rate: Decimal

    @classmethod
    def from_company(cls, company: CustomerCompany) -> "CustomerCompanyResponse":
        return cls.model_validate(company)

    model_config = ConfigDict(extra="forbid", from_attributes=True)


class CustomerProfileResponse(StrictSchema):
    id: UUID
    full_name: str
    email: str
    phone: str | None
    company: CustomerCompanyResponse | None

    @classmethod
    def from_customer(
        cls,
        customer: Customer,
        company: CustomerCompany | None,
    ) -> "CustomerProfileResponse":
        return cls(
            id=customer.id,
            full_name=customer.full_name,
            email=customer.email,
            phone=customer.phone,
            company=(
                CustomerCompanyResponse.from_company(company) if company else None
            ),
        )


class AdminCompanyResponse(CustomerCompanyResponse):
    customer_id: UUID
    customer_name: str
    customer_email: str
    created_at: datetime

    @classmethod
    def from_company_and_customer(
        cls,
        company: CustomerCompany,
        customer: Customer,
    ) -> "AdminCompanyResponse":
        return cls(
            **CustomerCompanyResponse.from_company(company).model_dump(),
            customer_id=customer.id,
            customer_name=customer.full_name,
            customer_email=customer.email,
            created_at=company.created_at,
        )


class CompanyListParams(PaginationParams):
    status: CompanyStatus | None = None


class CompanyListResponse(StrictSchema):
    items: list[AdminCompanyResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class ReviewCompanyRequest(StrictSchema):
    status: CompanyStatus
    manager_name: str | None = Field(default=None, max_length=120)
    cumulative_discount_rate: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        lt=1,
        max_digits=5,
        decimal_places=4,
    )

    @field_validator("manager_name", mode="before")
    @classmethod
    def normalize_manager_name(cls, value: object | None) -> str | None:
        return normalize_optional_text(value)

    @model_validator(mode="after")
    def reject_pending_review(self) -> "ReviewCompanyRequest":
        if self.status == CompanyStatus.PENDING:
            raise ValueError("A company cannot be returned to pending")
        return self
