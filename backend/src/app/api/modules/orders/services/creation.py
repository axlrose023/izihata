from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from app.api.common.exceptions import ConflictError, UnprocessableError
from app.api.modules.checkout.service import PricingService
from app.api.modules.orders.enums import OrderStatus, PaymentMethod, PaymentStatus
from app.api.modules.orders.models import Order, OrderItem
from app.api.modules.orders.schema import CreateOrderRequest, OrderResponse
from app.api.modules.orders.utils import new_order_number, request_digest
from app.api.modules.payments.enums import PaymentAttemptStatus
from app.api.modules.payments.models import PaymentAttempt
from app.api.modules.payments.schema import WayForPayWidgetSession
from app.api.modules.payments.service import WayForPayProvider
from app.api.modules.payments.utils import has_active_invoice
from app.database.uow import UnitOfWork


@dataclass(frozen=True, slots=True)
class OrderCreationOutcome:
    order: OrderResponse
    created: bool
    payment_attempt_id: UUID | None = None
    payment_widget: WayForPayWidgetSession | None = None


class OrderCreationService:
    def __init__(
        self,
        uow: UnitOfWork,
        pricing: PricingService,
        wayforpay: WayForPayProvider,
    ):
        self._uow = uow
        self._pricing = pricing
        self._wayforpay = wayforpay

    async def create_order(
        self,
        request: CreateOrderRequest,
        idempotency_key: str,
        customer_id: UUID | None = None,
        contact_email: str | None = None,
    ) -> OrderCreationOutcome:
        email = contact_email or request.email
        if email is None:
            raise ValueError("Order contact email is required")
        digest = request_digest(request.model_copy(update={"email": email}))
        existing = await self._uow.orders.get_by_idempotency_key(idempotency_key)
        if existing:
            return await self._existing_outcome(existing, digest)

        quote = await self._pricing.quote(request, customer_id=customer_id)
        if request.expected_total is not None and request.expected_total != quote.total:
            raise ConflictError(
                "Order total has changed; review the new quote", code="quote_changed"
            )
        if request.payment_method == PaymentMethod.CARD:
            if not self._wayforpay.enabled:
                raise UnprocessableError(
                    "Online card payment is temporarily unavailable",
                    code="payment_provider_unavailable",
                )
            self._wayforpay.split_customer_name(request.customer_name)
            if quote.total <= 0:
                raise UnprocessableError(
                    "Online card payment requires a positive order total",
                    code="payment_amount_invalid",
                )
        payment_status = (
            PaymentStatus.NOT_REQUIRED
            if request.payment_method == PaymentMethod.CASH_ON_DELIVERY
            else PaymentStatus.PENDING
        )
        company_name = request.company.name if request.company else None
        edrpou = request.company.edrpou if request.company else None
        order = Order(
            number=new_order_number(),
            idempotency_key=idempotency_key,
            request_hash=digest,
            customer_id=customer_id,
            customer_name=request.customer_name,
            email=email,
            phone=request.phone,
            company_name=company_name,
            edrpou=edrpou,
            delivery_method=request.delivery.method,
            delivery_city=request.delivery.city,
            delivery_point=request.delivery.point,
            payment_method=request.payment_method,
            payment_is_test=request.payment_method == PaymentMethod.CARD
            and self._wayforpay.test_mode,
            payment_status=payment_status,
            status=OrderStatus.NEW,
            promo_code=quote.promotion.code if quote.promotion else None,
            subtotal=quote.subtotal,
            discount=quote.discount,
            total=quote.total,
            items=[
                OrderItem(
                    product_id=item.product_id,
                    sku=item.sku,
                    product_name=item.name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    total=item.total,
                )
                for item in quote.items
            ],
        )
        try:
            await self._uow.orders.create(order)
            attempt = None
            widget = None
            if request.payment_method == PaymentMethod.CARD and self._wayforpay.enabled:
                attempt, widget = await self._create_payment_session(order)
            await self._uow.outbox.add(
                topic="order.created",
                payload={"order_id": str(order.id), "order_number": order.number},
            )
            await self._uow.commit()
        except IntegrityError as exc:
            await self._uow.rollback()
            concurrent = await self._uow.orders.get_by_idempotency_key(idempotency_key)
            if concurrent:
                return await self._existing_outcome(concurrent, digest)
            raise ConflictError("Order could not be created") from exc
        return OrderCreationOutcome(
            OrderResponse.from_order(order),
            created=True,
            payment_attempt_id=attempt.id if attempt else None,
            payment_widget=widget,
        )

    async def _existing_payment_session(
        self, order: Order
    ) -> tuple[UUID | None, WayForPayWidgetSession | None]:
        if order.payment_method != PaymentMethod.CARD or not self._wayforpay.enabled:
            return None, None
        attempt = await self._uow.payment_attempts.get_by_order_id(order.id)
        if order.payment_status in {PaymentStatus.PAID, PaymentStatus.REFUNDED}:
            return (attempt.id if attempt else None), None
        self._wayforpay.validate_order_mode(order)
        if order.total <= 0:
            raise UnprocessableError(
                "Online card payment requires a positive order total",
                code="payment_amount_invalid",
            )
        self._wayforpay.split_customer_name(order.customer_name)
        if attempt is None:
            attempt, _ = await self._create_payment_session(order)
            order.payment_status = PaymentStatus.PENDING
            await self._uow.commit()
        elif not attempt.invoice_url:
            raise ConflictError(
                "Previous payment is unconfirmed; contact the manager",
                code="payment_status_unconfirmed",
            )
        elif not has_active_invoice(attempt):
            raise ConflictError(
                "The payment invoice expired; contact the manager",
                code="payment_invoice_expired",
            )
        elif attempt.status == PaymentAttemptStatus.FAILED:
            attempt.status = PaymentAttemptStatus.PENDING
            order.payment_status = PaymentStatus.PENDING
            await self._uow.commit()
        return attempt.id, self._wayforpay.create_widget_session(order, attempt)

    async def _create_payment_session(
        self, order: Order
    ) -> tuple[PaymentAttempt, WayForPayWidgetSession]:
        attempt = await self._uow.payment_attempts.create(
            self._new_payment_attempt(order)
        )
        widget = self._wayforpay.create_widget_session(order, attempt)
        attempt.invoice_url = await self._wayforpay.create_invoice(widget)
        widget.invoice_url = attempt.invoice_url
        return attempt, widget

    @staticmethod
    def _new_payment_attempt(order: Order) -> PaymentAttempt:
        return PaymentAttempt(
            order_id=order.id,
            provider="wayforpay",
            order_reference=f"{order.number}-{uuid4().hex[:12]}",
            amount=order.total,
            currency="UAH",
            status=PaymentAttemptStatus.PENDING,
        )

    async def _existing_outcome(
        self, order: Order, digest: str
    ) -> OrderCreationOutcome:
        if order.request_hash != digest:
            raise ConflictError(
                "Idempotency key was already used for another request",
                code="idempotency_conflict",
            )
        attempt_id, widget = await self._existing_payment_session(order)
        return OrderCreationOutcome(
            OrderResponse.from_order(order),
            created=False,
            payment_attempt_id=attempt_id,
            payment_widget=widget,
        )
