from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.api.common.schema import StrictSchema
from app.api.modules.orders.enums import PaymentStatus


class WayForPayWidgetSession(StrictSchema):
    model_config = ConfigDict(
        extra="forbid", from_attributes=True, populate_by_name=True
    )

    merchant_account: str = Field(alias="merchantAccount")
    merchant_domain_name: str = Field(alias="merchantDomainName")
    authorization_type: str = Field(alias="authorizationType")
    merchant_transaction_secure_type: str = Field(alias="merchantTransactionSecureType")
    merchant_signature: str = Field(alias="merchantSignature")
    order_reference: str = Field(alias="orderReference")
    order_date: int = Field(alias="orderDate")
    amount: str
    currency: str
    product_name: list[str] = Field(alias="productName")
    product_price: list[str] = Field(alias="productPrice")
    product_count: list[int] = Field(alias="productCount")
    client_first_name: str = Field(alias="clientFirstName")
    client_last_name: str = Field(alias="clientLastName")
    client_email: str = Field(alias="clientEmail")
    client_phone: str = Field(alias="clientPhone")
    language: str
    service_url: str = Field(alias="serviceUrl")
    straight_widget: bool = Field(default=True, alias="straightWidget")
    invoice_url: str | None = Field(default=None, alias="invoiceUrl")


class WayForPayCallback(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    merchant_account: str = Field(alias="merchantAccount", min_length=1, max_length=128)
    order_reference: str = Field(alias="orderReference", min_length=1, max_length=64)
    merchant_signature: str = Field(
        alias="merchantSignature", pattern=r"^[0-9a-fA-F]{32}$"
    )
    amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)
    auth_code: str | None = Field(default=None, alias="authCode", max_length=128)
    card_pan: str | None = Field(default=None, alias="cardPan", max_length=32)
    transaction_status: str = Field(
        alias="transactionStatus", min_length=1, max_length=32
    )
    reason_code: str | int = Field(alias="reasonCode")


class WayForPayAcknowledgement(StrictSchema):
    model_config = ConfigDict(
        extra="forbid", from_attributes=True, populate_by_name=True
    )

    order_reference: str = Field(alias="orderReference")
    status: str
    time: int
    signature: str


class PaymentStatusResponse(StrictSchema):
    attempt_id: UUID
    status: PaymentStatus
    is_test: bool = False
    invoice_url: str | None = None


class PaymentAvailabilityResponse(StrictSchema):
    online_card_enabled: bool
    test_mode: bool = False
