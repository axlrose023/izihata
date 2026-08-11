import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.api.common.schema import PaginationParams, StrictSchema
from app.api.common.utils import (
    normalize_optional_text,
    normalize_phone,
    normalize_text,
)
from app.api.modules.checkout.schema import QuoteRequest
from app.api.modules.orders.enums import (
    DeliveryMethod,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
)
from app.api.modules.orders.models import Order


class DeliveryRequest(StrictSchema):
    method: DeliveryMethod
    city: str | None = Field(default=None, min_length=2, max_length=120)
    point: str | None = Field(default=None, min_length=1, max_length=200)

    @field_validator("city", "point", mode="before")
    @classmethod
    def normalize_destination(cls, value: object | None) -> str | None:
        return normalize_optional_text(value)

    @model_validator(mode="after")
    def validate_destination(self) -> "DeliveryRequest":
        if self.method != DeliveryMethod.PICKUP and (not self.city or not self.point):
            raise ValueError("city and point are required for carrier delivery")
        return self


class CompanyRequest(StrictSchema):
    name: str = Field(min_length=2, max_length=180)
    edrpou: str = Field(pattern=r"^\d{8,10}$")

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> str:
        return normalize_text(value)


class CreateOrderRequest(QuoteRequest):
    customer_name: str = Field(min_length=2, max_length=120)
    phone: str
    delivery: DeliveryRequest
    payment_method: PaymentMethod
    company: CompanyRequest | None = None

    @field_validator("customer_name", mode="before")
    @classmethod
    def normalize_customer_name(cls, value: object) -> str:
        return normalize_text(value)

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone_number(cls, value: object) -> str:
        return normalize_phone(value)

    @model_validator(mode="after")
    def validate_company_payment(self) -> "CreateOrderRequest":
        if self.payment_method == PaymentMethod.INVOICE and self.company is None:
            raise ValueError("company details are required for invoice payment")
        return self


class OrderItemResponse(StrictSchema):
    product_id: UUID
    sku: str
    product_name: str
    quantity: int
    unit_price: Decimal
    total: Decimal


class OrderResponse(StrictSchema):
    id: UUID
    number: str
    customer_name: str
    phone: str
    company: CompanyRequest | None
    delivery: DeliveryRequest
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    status: OrderStatus
    promo_code: str | None
    subtotal: Decimal
    discount: Decimal
    total: Decimal
    items: list[OrderItemResponse]
    created_at: datetime.datetime

    @classmethod
    def from_order(cls, order: Order) -> "OrderResponse":
        company = None
        if order.company_name and order.edrpou:
            company = CompanyRequest(name=order.company_name, edrpou=order.edrpou)
        return cls(
            id=order.id,
            number=order.number,
            customer_name=order.customer_name,
            phone=order.phone,
            company=company,
            delivery=DeliveryRequest(
                method=order.delivery_method,
                city=order.delivery_city,
                point=order.delivery_point,
            ),
            payment_method=order.payment_method,
            payment_status=order.payment_status,
            status=order.status,
            promo_code=order.promo_code,
            subtotal=order.subtotal,
            discount=order.discount,
            total=order.total,
            items=[
                OrderItemResponse(
                    product_id=item.product_id,
                    sku=item.sku,
                    product_name=item.product_name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    total=item.total,
                )
                for item in order.items
            ],
            created_at=order.created_at,
        )


class OrderListParams(PaginationParams):
    status: OrderStatus | None = None


class OrderSummaryResponse(StrictSchema):
    id: UUID
    number: str
    customer_name: str
    phone: str
    delivery: DeliveryRequest
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    status: OrderStatus
    total: Decimal
    created_at: datetime.datetime

    @classmethod
    def from_order(cls, order: Order) -> "OrderSummaryResponse":
        return cls(
            id=order.id,
            number=order.number,
            customer_name=order.customer_name,
            phone=order.phone,
            delivery=DeliveryRequest(
                method=order.delivery_method,
                city=order.delivery_city,
                point=order.delivery_point,
            ),
            payment_method=order.payment_method,
            payment_status=order.payment_status,
            status=order.status,
            total=order.total,
            created_at=order.created_at,
        )


class OrderListResponse(StrictSchema):
    items: list[OrderSummaryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class UpdateOrderStatusRequest(StrictSchema):
    status: OrderStatus
