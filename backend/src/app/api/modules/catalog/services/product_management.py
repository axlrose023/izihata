from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.api.common.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.api.modules.catalog.enums import StockStatus, StockSubscriptionStatus
from app.api.modules.catalog.models import (
    Category,
    Product,
    ProductAttribute,
    Subcategory,
)
from app.api.modules.catalog.schema import (
    CreateProductRequest,
    ProductResponse,
    UpdateProductRequest,
)
from app.api.modules.catalog.utils import product_slug_from_sku
from app.database.uow import UnitOfWork


class ProductManagementService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    @staticmethod
    def _replace_specs(product: Product, specs: dict[str, str]) -> None:
        existing = {attribute.key: attribute for attribute in product.attributes}
        attributes: list[ProductAttribute] = []
        for key, value in specs.items():
            attribute = existing.get(key)
            if attribute is None:
                attribute = ProductAttribute(key=key, value=value)
            else:
                attribute.value = value
            attributes.append(attribute)
        product.attributes = attributes

    @staticmethod
    def _is_available(status: StockStatus) -> bool:
        return status in {StockStatus.IN_STOCK_TODAY, StockStatus.IN_STOCK}

    async def _get_references(
        self,
        category_id: UUID,
        subcategory_id: UUID | None,
    ) -> tuple[Category, Subcategory | None]:
        category = await self._uow.categories.get_active_by_id(category_id)
        if category is None:
            raise NotFoundError("Category not found", code="category_not_found")

        if subcategory_id is None:
            return category, None

        subcategory = await self._uow.categories.get_active_subcategory_by_id(
            subcategory_id
        )
        if subcategory is None:
            raise NotFoundError(
                "Subcategory not found",
                code="subcategory_not_found",
            )
        if subcategory.category_id != category.id:
            raise UnprocessableError(
                "Subcategory does not belong to category",
                code="subcategory_category_mismatch",
            )
        return category, subcategory

    async def create_product(
        self,
        request: CreateProductRequest,
    ) -> ProductResponse:
        category, subcategory = await self._get_references(
            request.category_id,
            request.subcategory_id,
        )

        slug = product_slug_from_sku(request.sku)
        conflict = await self._uow.products.identity_conflict(request.sku, slug)
        if conflict is not None:
            raise ConflictError(
                f"Product {conflict} already exists",
                code=f"product_{conflict}_exists",
            )

        product = Product(
            category=category,
            subcategory=subcategory,
            sku=request.sku,
            slug=slug,
            name=request.name,
            brand=request.brand,
            brand_country=request.brand_country,
            production_country=request.production_country,
            short_description=request.short_description,
            description=request.description,
            image_url=request.image_url,
            price=request.price,
            old_price=request.old_price,
            badge=request.badge,
            stock_status=request.stock_status,
            availability_days=request.availability_days,
            sale_unit=request.sale_unit,
            wholesale_price=request.wholesale_price,
            wholesale_min_quantity=request.wholesale_min_quantity,
            position=await self._uow.products.next_position(),
            attributes=[
                ProductAttribute(key=key, value=value)
                for key, value in request.specs.items()
            ],
        )
        try:
            await self._uow.products.create(product)
            await self._uow.commit()
        except IntegrityError as error:
            await self._uow.rollback()
            raise ConflictError(
                "Product SKU or slug already exists",
                code="product_identity_exists",
            ) from error
        return ProductResponse.from_product(product)

    async def update_product(
        self,
        product_id: UUID,
        request: UpdateProductRequest,
    ) -> ProductResponse:
        product = await self._uow.products.get_by_id_for_update(product_id)
        if product is None:
            raise NotFoundError("Product not found")

        previous_stock_status = product.stock_status
        data = request.model_dump(exclude_unset=True)
        category_id = data.pop("category_id", product.category_id)
        subcategory_id = data.pop("subcategory_id", product.subcategory_id)
        if {"category_id", "subcategory_id"} & request.model_fields_set:
            category, subcategory = await self._get_references(
                category_id,
                subcategory_id,
            )
            product.category = category
            product.subcategory = subcategory

        specs = data.pop("specs", None)
        sku = data.get("sku", product.sku)
        slug = product_slug_from_sku(sku)
        if "sku" in data:
            conflict = await self._uow.products.identity_conflict(
                sku,
                slug,
                exclude_product_id=product.id,
            )
            if conflict is not None:
                raise ConflictError(
                    f"Product {conflict} already exists",
                    code=f"product_{conflict}_exists",
                )
            product.slug = slug

        resulting_price = data.get("price", product.price)
        resulting_old_price = data.get("old_price", product.old_price)
        resulting_wholesale_price = data.get(
            "wholesale_price",
            product.wholesale_price,
        )
        resulting_wholesale_min_quantity = data.get(
            "wholesale_min_quantity",
            product.wholesale_min_quantity,
        )
        if resulting_old_price is not None and resulting_old_price < resulting_price:
            raise UnprocessableError("old_price cannot be lower than price")
        if (resulting_wholesale_price is None) != (
            resulting_wholesale_min_quantity is None
        ):
            raise UnprocessableError(
                "Wholesale price and minimum quantity must be provided together",
                code="invalid_wholesale_price",
            )
        if (
            resulting_wholesale_price is not None
            and resulting_wholesale_price >= resulting_price
        ):
            raise UnprocessableError(
                "Wholesale price must be lower than retail price",
                code="invalid_wholesale_price",
            )
        for field, value in data.items():
            setattr(product, field, value)
        if specs is not None:
            self._replace_specs(product, specs)
        try:
            await self._uow.products.update(product)
            if not self._is_available(previous_stock_status) and self._is_available(
                product.stock_status
            ):
                await self._notify_stock_subscribers(product.id)
            await self._uow.commit()
        except IntegrityError as error:
            await self._uow.rollback()
            raise ConflictError(
                "Product SKU or slug already exists",
                code="product_identity_exists",
            ) from error
        return ProductResponse.from_product(product)

    async def _notify_stock_subscribers(self, product_id: UUID) -> None:
        subscriptions = await self._uow.products.active_stock_subscriptions(product_id)
        for subscription in subscriptions:
            subscription.status = StockSubscriptionStatus.NOTIFIED
            await self._uow.outbox.add(
                "catalog.back_in_stock",
                {
                    "subscription_id": str(subscription.id),
                    "product_id": str(product_id),
                },
            )
