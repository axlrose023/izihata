from datetime import UTC, datetime
from decimal import Decimal

from app.api.common.exceptions import UnprocessableError
from app.api.modules.checkout.schema import (
    AppliedPromotion,
    QuoteItemResponse,
    QuoteRequest,
    QuoteResponse,
)
from app.api.modules.checkout.utils import round_money
from app.database.uow import UnitOfWork


class PricingService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def quote(self, request: QuoteRequest) -> QuoteResponse:
        product_ids = [item.product_id for item in request.items]
        if len(product_ids) != len(set(product_ids)):
            raise UnprocessableError(
                "Duplicate products are not allowed",
                code="duplicate_products",
            )

        products = await self._uow.products.get_many(set(product_ids))
        products_by_id = {product.id: product for product in products}
        missing_ids = set(product_ids) - products_by_id.keys()
        if missing_ids:
            raise UnprocessableError(
                "One or more products are unavailable",
                code="products_unavailable",
            )

        quote_items: list[QuoteItemResponse] = []
        for item in request.items:
            product = products_by_id[item.product_id]
            line_total = round_money(product.price * item.quantity)
            quote_items.append(
                QuoteItemResponse(
                    product_id=product.id,
                    sku=product.sku,
                    name=product.name,
                    stock_status=product.stock_status,
                    quantity=item.quantity,
                    unit_price=round_money(product.price),
                    total=line_total,
                )
            )

        subtotal = round_money(sum((item.total for item in quote_items), Decimal(0)))
        promotion = None
        discount = Decimal("0.00")
        if request.promo_code:
            promotion_model = await self._uow.promotions.get_active_by_code(
                request.promo_code,
                datetime.now(UTC),
            )
            if promotion_model is None:
                raise UnprocessableError(
                    "Promotion code is invalid or expired",
                    code="promotion_invalid",
                )
            discount = round_money(subtotal * promotion_model.discount_rate)
            promotion = AppliedPromotion(
                code=promotion_model.code,
                discount_rate=promotion_model.discount_rate,
            )

        return QuoteResponse(
            items=quote_items,
            subtotal=subtotal,
            discount=discount,
            total=round_money(subtotal - discount),
            promotion=promotion,
        )
