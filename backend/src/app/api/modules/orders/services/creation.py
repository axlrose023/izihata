from sqlalchemy.exc import IntegrityError

from app.api.common.exceptions import ConflictError
from app.api.modules.checkout.service import PricingService
from app.api.modules.orders.enums import OrderStatus, PaymentMethod, PaymentStatus
from app.api.modules.orders.models import Order, OrderItem
from app.api.modules.orders.schema import CreateOrderRequest, OrderResponse
from app.api.modules.orders.utils import new_order_number, request_digest
from app.database.uow import UnitOfWork


class OrderCreationService:
    def __init__(self, uow: UnitOfWork, pricing: PricingService):
        self._uow = uow
        self._pricing = pricing

    async def create_order(
        self,
        request: CreateOrderRequest,
        idempotency_key: str,
    ) -> OrderResponse:
        digest = request_digest(request)
        existing = await self._uow.orders.get_by_idempotency_key(idempotency_key)
        if existing:
            return self._resolve_existing(existing, digest)

        quote = await self._pricing.quote(request)
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
            customer_name=request.customer_name,
            phone=request.phone,
            company_name=company_name,
            edrpou=edrpou,
            delivery_method=request.delivery.method,
            delivery_city=request.delivery.city,
            delivery_point=request.delivery.point,
            payment_method=request.payment_method,
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
            await self._uow.outbox.add(
                topic="order.created",
                payload={"order_id": str(order.id), "order_number": order.number},
            )
            await self._uow.commit()
        except IntegrityError as exc:
            await self._uow.rollback()
            concurrent = await self._uow.orders.get_by_idempotency_key(idempotency_key)
            if concurrent:
                return self._resolve_existing(concurrent, digest)
            raise ConflictError("Order could not be created") from exc
        return OrderResponse.from_order(order)

    def _resolve_existing(self, order: Order, digest: str) -> OrderResponse:
        if order.request_hash != digest:
            raise ConflictError("Idempotency key was already used for another request")
        return OrderResponse.from_order(order)
