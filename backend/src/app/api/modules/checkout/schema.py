from decimal import Decimal
from uuid import UUID

from pydantic import Field, field_validator

from app.api.common.schema import StrictSchema
from app.api.modules.catalog.enums import StockStatus


class QuoteItemRequest(StrictSchema):
    product_id: UUID
    quantity: int = Field(ge=1, le=999)


class QuoteRequest(StrictSchema):
    items: list[QuoteItemRequest] = Field(min_length=1, max_length=100)
    promo_code: str | None = Field(default=None, min_length=1, max_length=64)

    @field_validator("promo_code", mode="before")
    @classmethod
    def normalize_promo_code(cls, value: object | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Promotion code must be a string")
        return value.strip().upper()


class QuoteItemResponse(StrictSchema):
    product_id: UUID
    sku: str
    name: str
    stock_status: StockStatus
    quantity: int
    unit_price: Decimal
    total: Decimal


class AppliedPromotion(StrictSchema):
    code: str
    discount_rate: Decimal


class QuoteResponse(StrictSchema):
    items: list[QuoteItemResponse]
    subtotal: Decimal
    discount: Decimal
    total: Decimal
    promotion: AppliedPromotion | None
