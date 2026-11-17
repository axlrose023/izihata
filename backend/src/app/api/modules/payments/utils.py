from app.api.modules.payments.schema import WayForPayCallback


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
