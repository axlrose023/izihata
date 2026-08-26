from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from app.api.common.exceptions import UnprocessableError
from app.api.modules.catalog.models import Product
from app.api.modules.checkout.enums import QuotePriceType
from app.api.modules.checkout.schema import (
    AppliedPromotion,
    QuoteItemResponse,
    QuoteRequest,
    QuoteResponse,
)
from app.api.modules.checkout.utils import round_money
from app.api.modules.customers.enums import CompanyStatus
from app.database.uow import UnitOfWork


@dataclass(frozen=True, slots=True)
class PriceContext:
    company_verified: bool = False
    cumulative_discount_rate: Decimal = Decimal("0")


class PricingService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def quote(
        self,
        request: QuoteRequest,
        *,
        customer_id: UUID | None = None,
    ) -> QuoteResponse:
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

        context = await self._get_price_context(customer_id)
        quote_items: list[QuoteItemResponse] = []
        for item in request.items:
            product = products_by_id[item.product_id]
            unit_price, price_type = self._resolve_unit_price(
                product,
                item.quantity,
                context,
            )
            line_total = round_money(unit_price * item.quantity)
            quote_items.append(
                QuoteItemResponse(
                    product_id=product.id,
                    sku=product.sku,
                    name=product.name,
                    stock_status=product.stock_status,
                    quantity=item.quantity,
                    unit_price=unit_price,
                    total=line_total,
                    price_type=price_type,
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

    async def _get_price_context(self, customer_id: UUID | None) -> PriceContext:
        if customer_id is None:
            return PriceContext()

        company = await self._uow.customers.get_company_for_customer(customer_id)
        if company is None or company.status != CompanyStatus.APPROVED:
            return PriceContext()
        return PriceContext(
            company_verified=True,
            cumulative_discount_rate=company.cumulative_discount_rate,
        )

    @staticmethod
    def _resolve_unit_price(
        product: Product,
        quantity: int,
        context: PriceContext,
    ) -> tuple[Decimal, QuotePriceType]:
        wholesale_price = product.wholesale_price
        wholesale_min_quantity = product.wholesale_min_quantity
        if (
            wholesale_price is not None
            and wholesale_min_quantity is not None
            and (context.company_verified or quantity >= wholesale_min_quantity)
        ):
            price = wholesale_price
            price_type = QuotePriceType.WHOLESALE
        else:
            price = product.price
            price_type = QuotePriceType.RETAIL

        discount_multiplier = Decimal("1") - context.cumulative_discount_rate
        return round_money(price * discount_multiplier), price_type
