from uuid import UUID

from app.api.common.exceptions import NotFoundError, UnprocessableError
from app.api.modules.catalog.schema import ProductResponse, UpdateProductRequest
from app.database.uow import UnitOfWork


class ProductManagementService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def update_product(
        self,
        product_id: UUID,
        request: UpdateProductRequest,
    ) -> ProductResponse:
        product = await self._uow.products.get_by_id_for_update(product_id)
        if product is None:
            raise NotFoundError("Product not found")

        data = request.model_dump(exclude_unset=True)
        resulting_price = data.get("price", product.price)
        resulting_old_price = data.get("old_price", product.old_price)
        if resulting_old_price is not None and resulting_old_price < resulting_price:
            raise UnprocessableError("old_price cannot be lower than price")
        for field, value in data.items():
            setattr(product, field, value)
        await self._uow.products.update(product)
        await self._uow.commit()
        return ProductResponse.from_product(product)
