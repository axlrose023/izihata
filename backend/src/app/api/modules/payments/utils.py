from datetime import UTC, datetime, timedelta

from app.api.modules.payments.models import PaymentAttempt
from app.api.modules.payments.schema import WayForPayCallback

INVOICE_LIFETIME = timedelta(days=1)


def has_active_invoice(attempt: PaymentAttempt) -> bool:
    return bool(attempt.invoice_url) and datetime.now(UTC) < (
        attempt.created_at.replace(tzinfo=UTC) + INVOICE_LIFETIME
    )


def callback_signature_values(callback: WayForPayCallback) -> tuple[str, ...]:
    return (
        callback.merchant_account,
        callback.order_reference,
        format(callback.amount, "f"),
        callback.currency,
        callback.auth_code or "",
        callback.card_pan or "",
        callback.transaction_status,
        str(callback.reason_code),
    )
