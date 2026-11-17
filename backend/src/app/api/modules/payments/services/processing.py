from uuid import UUID

from app.api.common.exceptions import (
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
    UnauthorizedError,
)
from app.api.modules.orders.enums import PaymentMethod, PaymentStatus
from app.api.modules.payments.enums import PaymentAttemptStatus
from app.api.modules.payments.schema import (
    PaymentStatusResponse,
    WayForPayAcknowledgement,
    WayForPayCallback,
)
from app.api.modules.payments.services.wayforpay import WayForPayProvider
from app.database.uow import UnitOfWork


class WayForPayPaymentService:
    def __init__(self, uow: UnitOfWork, provider: WayForPayProvider):
        self._uow = uow
        self._provider = provider

    async def receive_callback(
        self, callback: WayForPayCallback
    ) -> WayForPayAcknowledgement:
        if not self._provider.enabled:
            raise ServiceUnavailableError(
                "WayForPay is not configured", code="payment_provider_unavailable"
            )
        if not self._provider.verify_callback(callback):
            raise UnauthorizedError("Invalid WayForPay signature")
        attempt = await self._uow.payment_attempts.get_by_reference_for_update(
            callback.order_reference
        )
        if attempt is None:
            raise NotFoundError("Payment attempt not found")
        if (
            attempt.provider != "wayforpay"
            or attempt.order.payment_method != PaymentMethod.CARD
        ):
            raise ConflictError("Payment attempt does not match this provider")
        if callback.amount != attempt.amount or callback.currency != attempt.currency:
            raise ConflictError("WayForPay payment amount does not match the order")

        latest_attempt = await self._uow.payment_attempts.get_by_order_id(
            attempt.order_id
        )
        transaction_status = callback.transaction_status.casefold()
        if (
            transaction_status == "approved"
            and attempt.status != PaymentAttemptStatus.REFUNDED
        ):
            attempt.status = PaymentAttemptStatus.PAID
            attempt.order.payment_status = PaymentStatus.PAID
        elif transaction_status in {"declined", "expired", "voided"}:
            if attempt.status not in {
                PaymentAttemptStatus.PAID,
                PaymentAttemptStatus.REFUNDED,
            }:
                attempt.status = PaymentAttemptStatus.FAILED
                if (
                    latest_attempt is not None
                    and latest_attempt.id == attempt.id
                    and attempt.order.payment_status
                    not in {PaymentStatus.PAID, PaymentStatus.REFUNDED}
                ):
                    attempt.order.payment_status = PaymentStatus.FAILED
        elif (
            transaction_status == "refunded"
            and attempt.status == PaymentAttemptStatus.PAID
        ):
            attempt.status = PaymentAttemptStatus.REFUNDED
            if not await self._uow.payment_attempts.has_other_paid_attempt(attempt):
                attempt.order.payment_status = PaymentStatus.REFUNDED

        await self._uow.commit()
        return self._provider.acknowledge(callback.order_reference)

    async def get_status(self, attempt_id: UUID) -> PaymentStatusResponse:
        attempt = await self._uow.payment_attempts.get_by_id(attempt_id)
        if attempt is None:
            raise NotFoundError("Payment attempt not found")
        return PaymentStatusResponse(
            attempt_id=attempt.id,
            status=PaymentAttemptStatus(attempt.order.payment_status.value),
        )
