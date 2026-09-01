from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.api.common.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.api.modules.catalog.enums import (
    AttributeValueType,
    StockStatus,
    StockSubscriptionStatus,
)
from app.api.modules.catalog.models import (
    CatalogAttribute,
    Category,
    Product,
    ProductAttribute,
    ProductDocument,
    ProductMedia,
    ProductRelation,
    Subcategory,
)
from app.api.modules.catalog.schema import (
    AdminProductDetailResponse,
    AdminProductResponse,
    CreateProductRequest,
    ProductDocumentInput,
    ProductMediaInput,
    ProductRelationInput,
    UpdateProductRequest,
)
from app.api.modules.catalog.utils import product_slug_from_sku
from app.database.uow import UnitOfWork


class ProductManagementService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def get_product(self, product_id: UUID) -> AdminProductDetailResponse:
        product = await self._uow.products.get_by_id(product_id)
        if product is None:
            raise NotFoundError("Product not found", code="product_not_found")
        relations = await self._uow.products.list_relations(product_id)
        return AdminProductDetailResponse.from_product(product, relations)

    async def _replace_specs(
        self,
        product: Product,
        specs: dict[str, str],
        *,
        category_id: UUID | None = None,
    ) -> None:
        assignments = await self._uow.categories.list_category_attributes(
            category_id or product.category_id
        )
        definitions_by_name = {
            definition.name: definition for _, definition in assignments
        }
        if assignments:
            unknown_names = set(specs) - definitions_by_name.keys()
            if unknown_names:
                raise UnprocessableError(
                    "Product contains attributes not configured for its category",
                    code="unknown_product_attribute",
                )
            required_names = {
                definition.name
                for assignment, definition in assignments
                if assignment.is_required
            }
            missing_required_names = required_names - specs.keys()
            if missing_required_names:
                raise UnprocessableError(
                    "Product is missing required category attributes",
                    code="required_product_attribute_missing",
                )

        existing = {attribute.key: attribute for attribute in product.attributes}
        attributes: list[ProductAttribute] = []
        for key, value in specs.items():
            definition = definitions_by_name.get(key)
            attribute = existing.get(key)
            if attribute is None:
                attribute = ProductAttribute(key=key, value=value)
            else:
                attribute.value = value
            attribute.attribute_id = definition.id if definition is not None else None
            attribute.numeric_value = self._numeric_attribute_value(value, definition)
            attributes.append(attribute)
        product.attributes = attributes

    @staticmethod
    def _numeric_attribute_value(
        value: str,
        definition: CatalogAttribute | None,
    ) -> Decimal | None:
        if definition is None or definition.value_type != AttributeValueType.NUMBER:
            return None
        normalized = value.replace(",", ".").split()[0]
        try:
            return Decimal(normalized)
        except InvalidOperation as exc:
            raise UnprocessableError(
                f"Attribute '{definition.name}' must be numeric",
                code="invalid_numeric_product_attribute",
            ) from exc

    @staticmethod
    def _replace_media(product: Product, media: list[ProductMediaInput]) -> None:
        product.media = [
            ProductMedia(url=item.url, alt=item.alt, position=item.position)
            for item in media
        ]
        if media:
            product.image_url = media[0].url

    @staticmethod
    def _replace_documents(
        product: Product,
        documents: list[ProductDocumentInput],
    ) -> None:
        product.documents = [
            ProductDocument(
                kind=item.kind,
                title=item.title,
                url=item.url,
                position=item.position,
            )
            for item in documents
        ]

    @staticmethod
    def _is_available(status: StockStatus) -> bool:
        return status in {StockStatus.IN_STOCK_TODAY, StockStatus.IN_STOCK}

    @staticmethod
    def _validate_price_configuration(
        *,
        price: Decimal,
        old_price: Decimal | None,
        wholesale_price: Decimal | None,
        wholesale_min_quantity: int | None,
    ) -> None:
        if old_price is not None and old_price < price:
            raise UnprocessableError("old_price cannot be lower than price")
        if (wholesale_price is None) != (wholesale_min_quantity is None):
            raise UnprocessableError(
                "Wholesale price and minimum quantity must be provided together",
                code="invalid_wholesale_price",
            )
        if wholesale_price is not None and wholesale_price >= price:
            raise UnprocessableError(
                "Wholesale price must be lower than retail price",
                code="invalid_wholesale_price",
            )

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
    ) -> AdminProductResponse:
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
            attributes=[],
            media=[
                ProductMedia(url=item.url, alt=item.alt, position=item.position)
                for item in request.media
            ],
            documents=[
                ProductDocument(
                    kind=item.kind,
                    title=item.title,
                    url=item.url,
                    position=item.position,
                )
                for item in request.documents
            ],
        )
        await self._replace_specs(product, request.specs, category_id=category.id)
        if request.media:
            product.image_url = request.media[0].url
        try:
            await self._uow.products.create(product)
            await self._replace_relations(product.id, request.relations)
            await self._uow.commit()
        except IntegrityError as error:
            await self._uow.rollback()
            raise ConflictError(
                "Product SKU or slug already exists",
                code="product_identity_exists",
            ) from error
        return AdminProductResponse.from_product(product)

    async def update_product(
        self,
        product_id: UUID,
        request: UpdateProductRequest,
    ) -> AdminProductResponse:
        product = await self._uow.products.get_by_id_for_update(product_id)
        if product is None:
            raise NotFoundError("Product not found")

        previous_stock_status = product.stock_status
        data = request.model_dump(exclude_unset=True)
        category_id = data.pop("category_id", product.category_id)
        subcategory_id = data.pop("subcategory_id", product.subcategory_id)
        category_changed = category_id != product.category_id
        if {"category_id", "subcategory_id"} & request.model_fields_set:
            category, subcategory = await self._get_references(
                category_id,
                subcategory_id,
            )
            product.category = category
            product.subcategory = subcategory

        specs = data.pop("specs", None)
        data.pop("media", None)
        data.pop("documents", None)
        data.pop("relations", None)
        media = request.media if "media" in request.model_fields_set else None
        documents = (
            request.documents if "documents" in request.model_fields_set else None
        )
        relations = (
            request.relations if "relations" in request.model_fields_set else None
        )
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
        self._validate_price_configuration(
            price=resulting_price,
            old_price=resulting_old_price,
            wholesale_price=resulting_wholesale_price,
            wholesale_min_quantity=resulting_wholesale_min_quantity,
        )
        for field, value in data.items():
            setattr(product, field, value)
        if specs is not None:
            await self._replace_specs(product, specs, category_id=category_id)
        elif category_changed:
            await self._replace_specs(
                product,
                {attribute.key: attribute.value for attribute in product.attributes},
                category_id=category_id,
            )
        if media is not None:
            self._replace_media(product, media)
        if documents is not None:
            self._replace_documents(product, documents)
        try:
            await self._uow.products.update(product)
            if relations is not None:
                await self._replace_relations(product.id, relations)
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
        return AdminProductResponse.from_product(product)

    async def _replace_relations(
        self,
        source_product_id: UUID,
        relation_inputs: list[ProductRelationInput],
    ) -> None:
        target_product_ids = {item.product_id for item in relation_inputs}
        if source_product_id in target_product_ids:
            raise UnprocessableError(
                "A product cannot be related to itself",
                code="invalid_product_relation",
            )
        targets = await self._uow.products.get_many(target_product_ids)
        if len(targets) != len(target_product_ids):
            raise NotFoundError(
                "Related product not found",
                code="related_product_not_found",
            )
        await self._uow.products.replace_relations(
            source_product_id,
            [
                ProductRelation(
                    source_product_id=source_product_id,
                    target_product_id=item.product_id,
                    kind=item.kind,
                    position=item.position,
                )
                for item in relation_inputs
            ],
        )

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
