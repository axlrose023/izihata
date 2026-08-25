from sqlalchemy.exc import IntegrityError

from app.api.common.exceptions import NotFoundError, UnprocessableError
from app.api.modules.catalog.enums import StockStatus, StockSubscriptionStatus
from app.api.modules.catalog.models import ProductStockSubscription
from app.api.modules.catalog.schema import (
    CreateStockSubscriptionRequest,
    StockSubscriptionResponse,
)
from app.database.uow import UnitOfWork


class StockSubscriptionService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def subscribe(
        self,
        product_slug: str,
        request: CreateStockSubscriptionRequest,
    ) -> StockSubscriptionResponse:
        product = await self._uow.products.get_by_slug(product_slug)
        if product is None:
            raise NotFoundError("Product not found")
        if product.stock_status != StockStatus.OUT_OF_STOCK:
            raise UnprocessableError(
                "Product is currently available",
                code="product_is_available",
            )

        subscription = await self._uow.products.get_stock_subscription(
            product.id,
            request.email,
        )
        if subscription is None:
            subscription = ProductStockSubscription(
                product_id=product.id,
                email=request.email,
            )
            try:
                await self._uow.products.create_stock_subscription(subscription)
                await self._uow.commit()
            except IntegrityError:
                await self._uow.rollback()
                subscription = await self._uow.products.get_stock_subscription(
                    product.id,
                    request.email,
                )
                if subscription is None:
                    raise
        elif subscription.status != StockSubscriptionStatus.ACTIVE:
            subscription.status = StockSubscriptionStatus.ACTIVE
            await self._uow.commit()

        return StockSubscriptionResponse(id=subscription.id, status=subscription.status)
