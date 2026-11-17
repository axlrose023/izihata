import hashlib
import hmac
import re
from datetime import UTC, datetime
from decimal import Decimal
from urllib.parse import urlsplit

import httpx

from app.api.common.exceptions import (
    ConflictError,
    ServiceUnavailableError,
    UnprocessableError,
)
from app.api.modules.orders.models import Order
from app.api.modules.payments.models import PaymentAttempt
from app.api.modules.payments.schema import (
    WayForPayAcknowledgement,
    WayForPayCallback,
    WayForPayWidgetSession,
)
from app.api.modules.payments.utils import INVOICE_LIFETIME, callback_signature_values
from app.settings import Config, WayForPayConfig


class WayForPayProvider:
    def __init__(self, config: Config):
        self._config = config.wayforpay
        self._api_prefix = config.api.prefix.rstrip("/")

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    @property
    def test_mode(self) -> bool:
        return self._config.test_mode

    def validate_order_mode(self, order: Order) -> None:
        if order.payment_is_test != self.test_mode:
            raise ConflictError(
                "Payment mode has changed; contact the manager",
                code="payment_mode_changed",
            )

    def create_widget_session(
        self,
        order: Order,
        attempt: PaymentAttempt,
    ) -> WayForPayWidgetSession:
        config = self._require_config()
        self.validate_order_mode(order)
        if not config.merchant_account or not config.merchant_domain_name:
            raise ServiceUnavailableError(
                "WayForPay is not configured", code="payment_provider_unavailable"
            )
        first_name, last_name = self.split_customer_name(order.customer_name)
        amount = self._money(order.total)
        order_date = int(attempt.created_at.replace(tzinfo=UTC).timestamp())
        names, prices, counts = self._product_lines(order)
        signature_values = (
            config.merchant_account,
            config.merchant_domain_name,
            attempt.order_reference,
            str(order_date),
            amount,
            "UAH",
            *names,
            *(str(count) for count in counts),
            *prices,
        )
        return WayForPayWidgetSession(
            merchant_account=config.merchant_account,
            merchant_domain_name=config.merchant_domain_name,
            authorization_type="SimpleSignature",
            merchant_transaction_secure_type="AUTO",
            merchant_signature=self._sign(signature_values, config),
            order_reference=attempt.order_reference,
            order_date=order_date,
            amount=amount,
            currency="UAH",
            product_name=names,
            product_price=prices,
            product_count=counts,
            client_first_name="Test" if config.test_mode else first_name,
            client_last_name="Payment" if config.test_mode else last_name,
            client_email="test@example.invalid"
            if config.test_mode
            else order.email or "",
            client_phone="380500000000"
            if config.test_mode
            else re.sub(r"\D", "", order.phone),
            language="UA",
            service_url=(
                f"https://{config.merchant_domain_name}"
                f"{self._api_prefix}/payments/wayforpay/callback"
            ),
            straight_widget=True,
            invoice_url=attempt.invoice_url,
        )

    async def create_invoice(self, session: WayForPayWidgetSession) -> str:
        fields = session.model_dump(by_alias=True, exclude={"invoice_url"})
        fields.update(
            transactionType="CREATE_INVOICE",
            merchantAuthType="SimpleSignature",
            apiVersion=1,
            orderTimeout=int(INVOICE_LIFETIME.total_seconds()),
        )
        # Do not notify the customer before the order transaction is committed.
        for field in (
            "authorizationType",
            "merchantTransactionSecureType",
            "straightWidget",
            "clientEmail",
            "clientPhone",
        ):
            fields.pop(field, None)
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(10, connect=3)
            ) as client:
                response = await client.post(
                    "https://api.wayforpay.com/api", json=fields
                )
                response.raise_for_status()
                data = response.json()
            url = data.get("invoiceUrl") if isinstance(data, dict) else None
            parsed = urlsplit(url) if isinstance(url, str) else None
            if (
                not isinstance(data, dict)
                or str(data.get("reasonCode")) != "1100"
                or not isinstance(url, str)
                or parsed is None
                or parsed.scheme != "https"
                or parsed.netloc != "secure.wayforpay.com"
                or not parsed.path.startswith("/invoice/")
                or len(url) > 512
            ):
                raise ValueError("Invalid WayForPay invoice response")
            return url
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise ServiceUnavailableError(
                "Could not prepare online payment",
                code="payment_provider_unavailable",
            ) from exc

    def verify_callback(self, callback: WayForPayCallback) -> bool:
        config = self._require_config()
        if callback.merchant_account != config.merchant_account:
            return False
        expected = self._sign(callback_signature_values(callback), config)
        return hmac.compare_digest(expected, callback.merchant_signature.lower())

    def acknowledge(self, order_reference: str) -> WayForPayAcknowledgement:
        config = self._require_config()
        timestamp = int(datetime.now(UTC).timestamp())
        signature = self._sign((order_reference, "accept", str(timestamp)), config)
        return WayForPayAcknowledgement(
            order_reference=order_reference,
            status="accept",
            time=timestamp,
            signature=signature,
        )

    @staticmethod
    def split_customer_name(full_name: str) -> tuple[str, str]:
        parts = full_name.split(maxsplit=1)
        if len(parts) != 2:
            raise UnprocessableError(
                "Для онлайн-оплати вкажіть ім'я та прізвище",
                code="payment_customer_name_required",
            )
        return parts[0], parts[1]

    @classmethod
    def _product_lines(cls, order: Order) -> tuple[list[str], list[str], list[int]]:
        # A promotion discount is order-level. Send a single exact-price line so
        # the payment page total cannot disagree with the signed amount.
        if order.discount > Decimal("0"):
            quantity = sum(item.quantity for item in order.items)
            return (
                [f"Замовлення {order.number} ({quantity} товарів)"],
                [cls._money(order.total)],
                [1],
            )
        return (
            [item.product_name for item in order.items],
            [cls._money(item.unit_price) for item in order.items],
            [item.quantity for item in order.items],
        )

    @staticmethod
    def _money(amount: Decimal) -> str:
        return format(amount.quantize(Decimal("0.01")), ".2f")

    @staticmethod
    def _sign(values: tuple[str, ...], config: WayForPayConfig) -> str:
        if config.secret_key is None:
            raise ServiceUnavailableError(
                "WayForPay is not configured", code="payment_provider_unavailable"
            )
        message = ";".join(values).encode("utf-8")
        secret = config.secret_key.get_secret_value().encode("utf-8")
        # WayForPay requires HMAC-MD5 for this protocol.
        return hmac.new(secret, message, hashlib.md5).hexdigest()

    def _require_config(self) -> WayForPayConfig:
        if not self._config.enabled:
            raise ServiceUnavailableError(
                "Online card payment is not configured",
                code="payment_provider_unavailable",
            )
        return self._config
