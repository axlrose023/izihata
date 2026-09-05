from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.api.common.schema import PaginationParams, StrictSchema
from app.api.common.utils import normalize_optional_text, normalize_text
from app.api.modules.catalog.enums import (
    AttributeValueType,
    ProductBadge,
    ProductDocumentKind,
    ProductRelationKind,
    ProductSort,
    ReviewStatus,
    SaleUnit,
    StockStatus,
    StockSubscriptionStatus,
)
from app.api.modules.catalog.models import (
    CatalogAttribute,
    CatalogSection,
    Product,
    ProductDocument,
    ProductMedia,
    ProductRelation,
    ProductReview,
)
from app.api.modules.catalog.utils import (
    normalize_image_url,
    normalize_product_specs,
    normalize_sku,
)


class CatalogReference(StrictSchema):
    id: UUID
    slug: str
    name: str


class SubcategoryResponse(CatalogReference):
    product_count: int


class CategoryResponse(CatalogReference):
    accent: str
    product_count: int
    subcategories: list[SubcategoryResponse]


class CatalogSectionResponse(CatalogReference):
    description: str | None
    image_url: str | None
    product_count: int
    categories: list[CategoryResponse]

    @classmethod
    def from_section(
        cls,
        section: CatalogSection,
        category_counts: dict[UUID, int],
        subcategory_counts: dict[UUID, int],
    ) -> "CatalogSectionResponse":
        categories = [
            CategoryResponse(
                id=category.id,
                slug=category.slug,
                name=category.name,
                accent=category.accent,
                product_count=category_counts.get(category.id, 0),
                subcategories=[
                    SubcategoryResponse(
                        id=subcategory.id,
                        slug=subcategory.slug,
                        name=subcategory.name,
                        product_count=subcategory_counts.get(subcategory.id, 0),
                    )
                    for subcategory in category.subcategories
                    if subcategory.is_active
                ],
            )
            for category in section.categories
            if category.is_active
        ]
        return cls(
            id=section.id,
            slug=section.slug,
            name=section.name,
            description=section.description,
            image_url=section.image_url,
            product_count=sum(category.product_count for category in categories),
            categories=categories,
        )


class ProductAvailabilityResponse(StrictSchema):
    status: StockStatus
    lead_time_days: int | None
    dispatch_cutoff_hour: int | None


class ProductMediaResponse(StrictSchema):
    id: UUID
    url: str
    alt: str
    position: int

    @classmethod
    def from_media(cls, media: ProductMedia) -> "ProductMediaResponse":
        return cls.model_validate(media)

    model_config = ConfigDict(extra="forbid", from_attributes=True)


class ProductDocumentResponse(StrictSchema):
    id: UUID
    kind: ProductDocumentKind
    title: str
    url: str

    @classmethod
    def from_document(cls, document: ProductDocument) -> "ProductDocumentResponse":
        return cls.model_validate(document)

    model_config = ConfigDict(extra="forbid", from_attributes=True)


class ProductResponse(StrictSchema):
    id: UUID
    sku: str
    slug: str
    name: str
    brand: str
    brand_country: str | None
    production_country: str | None
    short_description: str | None
    image_url: str | None
    price: Decimal
    old_price: Decimal | None
    badge: ProductBadge | None
    stock_status: StockStatus
    availability: ProductAvailabilityResponse
    sale_unit: SaleUnit
    wholesale_min_quantity: int | None
    rating: Decimal
    reviews_count: int
    category: CatalogReference
    subcategory: CatalogReference | None
    specs: dict[str, str]

    @classmethod
    def from_product(cls, product: Product) -> "ProductResponse":
        return cls(
            id=product.id,
            sku=product.sku,
            slug=product.slug,
            name=product.name,
            brand=product.brand,
            brand_country=product.brand_country,
            production_country=product.production_country,
            short_description=product.short_description,
            image_url=product.image_url,
            price=product.price,
            old_price=product.old_price,
            badge=product.badge,
            stock_status=product.stock_status,
            availability=ProductAvailabilityResponse(
                status=product.stock_status,
                lead_time_days=product.availability_days,
                dispatch_cutoff_hour=(
                    14 if product.stock_status == StockStatus.IN_STOCK_TODAY else None
                ),
            ),
            sale_unit=product.sale_unit,
            wholesale_min_quantity=product.wholesale_min_quantity,
            rating=product.rating,
            reviews_count=product.reviews_count,
            category=CatalogReference.model_validate(product.category),
            subcategory=(
                CatalogReference.model_validate(product.subcategory)
                if product.subcategory
                else None
            ),
            specs={attribute.key: attribute.value for attribute in product.attributes},
        )

    model_config = ConfigDict(extra="forbid", from_attributes=True)


class ProductReviewResponse(StrictSchema):
    id: UUID
    author: str
    rating: int
    text: str
    created_at: datetime

    @classmethod
    def from_review(cls, review: ProductReview) -> "ProductReviewResponse":
        return cls.model_validate(review)

    model_config = ConfigDict(extra="forbid", from_attributes=True)


class ProductDetailResponse(ProductResponse):
    description: str | None
    media: list[ProductMediaResponse]
    documents: list[ProductDocumentResponse]
    reviews: list[ProductReviewResponse]
    related: list[ProductResponse]
    alternatives: list[ProductResponse]
    bought_together: list[ProductResponse]

    @classmethod
    def from_product(
        cls,
        product: Product,
        *,
        related: list[Product] | None = None,
        alternatives: list[Product] | None = None,
        bought_together: list[Product] | None = None,
    ) -> "ProductDetailResponse":
        summary = ProductResponse.from_product(product)
        return cls(
            **summary.model_dump(),
            description=product.description,
            media=[ProductMediaResponse.from_media(media) for media in product.media],
            documents=[
                ProductDocumentResponse.from_document(document)
                for document in product.documents
            ],
            reviews=[
                ProductReviewResponse.from_review(review)
                for review in product.reviews
                if review.is_published
            ],
            related=[ProductResponse.from_product(item) for item in related or []],
            alternatives=[
                ProductResponse.from_product(item) for item in alternatives or []
            ],
            bought_together=[
                ProductResponse.from_product(item) for item in bought_together or []
            ],
        )


class FacetOption(StrictSchema):
    value: str
    count: int


class PriceFacet(StrictSchema):
    minimum: Decimal | None
    maximum: Decimal | None


class ProductFacets(StrictSchema):
    brands: list[FacetOption]
    specs: dict[str, list[FacetOption]]
    availability: list[FacetOption]
    sale_units: list[FacetOption]
    price: PriceFacet


class CatalogAttributeResponse(StrictSchema):
    id: UUID
    code: str
    name: str
    value_type: AttributeValueType
    unit: str | None
    is_filterable: bool
    position: int

    @classmethod
    def from_attribute(cls, attribute: CatalogAttribute) -> "CatalogAttributeResponse":
        return cls.model_validate(attribute)

    model_config = ConfigDict(extra="forbid", from_attributes=True)


class ProductListParams(PaginationParams):
    product_ids: list[UUID] = Field(
        default_factory=list,
        alias="id",
        max_length=100,
    )
    search: str | None = Field(default=None, min_length=2, max_length=120)
    category: str | None = Field(default=None, min_length=1, max_length=64)
    section: str | None = Field(default=None, min_length=1, max_length=64)
    subcategory: str | None = Field(default=None, min_length=1, max_length=96)
    brand: list[str] = Field(default_factory=list)
    badge: list[ProductBadge] = Field(default_factory=list, max_length=6)
    in_stock: bool = False
    availability: list[StockStatus] = Field(default_factory=list, max_length=4)
    sale_unit: list[SaleUnit] = Field(default_factory=list, max_length=3)
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, ge=0)
    spec: list[str] = Field(default_factory=list)
    sort: ProductSort = ProductSort.POPULAR

    @field_validator("product_ids")
    @classmethod
    def validate_product_ids(cls, values: list[UUID]) -> list[UUID]:
        return list(dict.fromkeys(values))

    @field_validator("search", "section", "category", "subcategory", mode="before")
    @classmethod
    def normalize_filters(cls, value: object | None) -> str | None:
        return normalize_optional_text(value)

    @field_validator("brand")
    @classmethod
    def validate_brands(cls, values: list[str]) -> list[str]:
        if len(values) > 20 or any(not value.strip() for value in values):
            raise ValueError("At most 20 non-empty brand filters are allowed")
        return list(dict.fromkeys(value.strip() for value in values))

    @field_validator("spec")
    @classmethod
    def validate_specs(cls, values: list[str]) -> list[str]:
        if len(values) > 30:
            raise ValueError("At most 30 specification filters are allowed")
        for value in values:
            key, separator, option = value.partition(":")
            if not separator or not key.strip() or not option.strip():
                raise ValueError("Specification filters must use 'key:value' format")
        return values

    @model_validator(mode="after")
    def validate_price_range(self) -> "ProductListParams":
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError("min_price cannot exceed max_price")
        return self

    @property
    def spec_filters(self) -> dict[str, set[str]]:
        filters: dict[str, set[str]] = {}
        for raw_filter in self.spec:
            key, _, value = raw_filter.partition(":")
            filters.setdefault(key.strip(), set()).add(value.strip())
        return filters


class ProductListResponse(StrictSchema):
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
    facets: ProductFacets


class CreateProductReviewRequest(StrictSchema):
    author: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    rating: int = Field(ge=1, le=5)
    text: str = Field(min_length=10, max_length=4000)

    @field_validator("author", "text", mode="before")
    @classmethod
    def normalize_review_text(cls, value: object) -> str:
        return normalize_text(value)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> str:
        from app.api.modules.catalog.utils import normalize_email

        return normalize_email(value)


class CreateProductReviewResponse(StrictSchema):
    id: UUID
    status: ReviewStatus


class CreateStockSubscriptionRequest(StrictSchema):
    email: str = Field(min_length=3, max_length=254)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> str:
        from app.api.modules.catalog.utils import normalize_email

        return normalize_email(value)


class StockSubscriptionResponse(StrictSchema):
    id: UUID
    status: StockSubscriptionStatus


class ProductMediaInput(StrictSchema):
    url: str = Field(min_length=1, max_length=500)
    alt: str = Field(min_length=2, max_length=240)
    position: int = Field(default=0, ge=0, le=100)

    @field_validator("url", mode="before")
    @classmethod
    def validate_url(cls, value: object) -> str:
        normalized = normalize_image_url(value)
        if normalized is None:
            raise ValueError("Media URL is required")
        return normalized

    @field_validator("alt", mode="before")
    @classmethod
    def normalize_alt(cls, value: object) -> str:
        return normalize_text(value)


class ProductDocumentInput(StrictSchema):
    kind: ProductDocumentKind = ProductDocumentKind.CERTIFICATE
    title: str = Field(min_length=2, max_length=240)
    url: str = Field(min_length=1, max_length=500)
    position: int = Field(default=0, ge=0, le=100)

    @field_validator("title", mode="before")
    @classmethod
    def normalize_title(cls, value: object) -> str:
        return normalize_text(value)

    @field_validator("url", mode="before")
    @classmethod
    def validate_url(cls, value: object) -> str:
        normalized = normalize_image_url(value)
        if normalized is None:
            raise ValueError("Document URL is required")
        return normalized


class ProductRelationInput(StrictSchema):
    product_id: UUID
    kind: ProductRelationKind
    position: int = Field(default=0, ge=0, le=100)


class AdminProductRelationResponse(StrictSchema):
    product_id: UUID
    kind: ProductRelationKind
    position: int
    name: str
    sku: str

    @classmethod
    def from_relation(
        cls,
        relation: ProductRelation,
        target: Product,
    ) -> "AdminProductRelationResponse":
        return cls(
            product_id=target.id,
            kind=relation.kind,
            position=relation.position,
            name=target.name,
            sku=target.sku,
        )


class AdminProductResponse(ProductResponse):
    wholesale_price: Decimal | None

    @classmethod
    def from_product(cls, product: Product) -> "AdminProductResponse":
        return cls(
            **ProductResponse.from_product(product).model_dump(),
            wholesale_price=product.wholesale_price,
        )


class AdminProductDetailResponse(AdminProductResponse):
    description: str | None
    relations: list[AdminProductRelationResponse]

    @classmethod
    def from_product(  # type: ignore[override]
        cls,
        product: Product,
        relations: Sequence[tuple[ProductRelation, Product]] = (),
    ) -> "AdminProductDetailResponse":
        summary = AdminProductResponse.from_product(product)
        return cls(
            **summary.model_dump(),
            description=product.description,
            relations=[
                AdminProductRelationResponse.from_relation(relation, target)
                for relation, target in relations
            ],
        )


class CreateCatalogSectionRequest(StrictSchema):
    slug: str = Field(
        min_length=2, max_length=64, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )
    name: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    image_url: str | None = Field(default=None, max_length=500)
    position: int = Field(default=0, ge=0, le=1000)

    @field_validator("name", "description", mode="before")
    @classmethod
    def normalize_text_fields(cls, value: object | None) -> str | None:
        return normalize_optional_text(value)

    @field_validator("image_url", mode="before")
    @classmethod
    def validate_image_url(cls, value: object | None) -> str | None:
        return normalize_image_url(value)


class AdminCatalogSectionResponse(StrictSchema):
    id: UUID
    slug: str
    name: str
    description: str | None
    image_url: str | None
    position: int
    is_active: bool

    model_config = ConfigDict(extra="forbid", from_attributes=True)


class UpdateCatalogSectionRequest(StrictSchema):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    image_url: str | None = Field(default=None, max_length=500)
    position: int | None = Field(default=None, ge=0, le=1000)
    is_active: bool | None = None

    @field_validator("name", "description", mode="before")
    @classmethod
    def normalize_text_fields(cls, value: object | None) -> str | None:
        return normalize_optional_text(value)

    @field_validator("image_url", mode="before")
    @classmethod
    def validate_image_url(cls, value: object | None) -> str | None:
        return normalize_image_url(value)

    @model_validator(mode="after")
    def require_update(self) -> "UpdateCatalogSectionRequest":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class CreateCatalogAttributeRequest(StrictSchema):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=2, max_length=120)
    value_type: AttributeValueType = AttributeValueType.SELECT
    unit: str | None = Field(default=None, max_length=32)
    is_filterable: bool = True
    position: int = Field(default=0, ge=0, le=1000)

    @field_validator("name", "unit", mode="before")
    @classmethod
    def normalize_text_fields(cls, value: object | None) -> str | None:
        return normalize_optional_text(value)


class CategoryAttributeInput(StrictSchema):
    attribute_id: UUID
    is_required: bool = False
    is_primary_filter: bool = False
    position: int = Field(default=0, ge=0, le=1000)


class ReplaceCategoryAttributesRequest(StrictSchema):
    attributes: list[CategoryAttributeInput] = Field(
        default_factory=list, max_length=50
    )

    @model_validator(mode="after")
    def validate_unique_attributes(self) -> "ReplaceCategoryAttributesRequest":
        attribute_ids = [item.attribute_id for item in self.attributes]
        if len(attribute_ids) != len(set(attribute_ids)):
            raise ValueError("Attribute IDs must be unique")
        return self


class UpdateCategorySectionRequest(StrictSchema):
    section_id: UUID | None = None

    @model_validator(mode="after")
    def require_update(self) -> "UpdateCategorySectionRequest":
        if "section_id" not in self.model_fields_set:
            raise ValueError("section_id must be provided")
        return self


class ReviewModerationRequest(StrictSchema):
    status: ReviewStatus
    is_featured: bool = False

    @model_validator(mode="after")
    def validate_status(self) -> "ReviewModerationRequest":
        if self.status == ReviewStatus.PENDING:
            raise ValueError("A review cannot be returned to pending")
        if self.status != ReviewStatus.PUBLISHED and self.is_featured:
            raise ValueError("Only published reviews can be featured")
        return self


class AdminProductReviewResponse(StrictSchema):
    id: UUID
    product_id: UUID
    product_name: str
    author: str
    email: str | None
    rating: int
    text: str
    status: ReviewStatus
    is_featured: bool
    created_at: datetime

    @classmethod
    def from_review(
        cls,
        review: ProductReview,
        product: Product,
    ) -> "AdminProductReviewResponse":
        return cls(
            id=review.id,
            product_id=product.id,
            product_name=product.name,
            author=review.author,
            email=review.email,
            rating=review.rating,
            text=review.text,
            status=review.status,
            is_featured=review.is_featured,
            created_at=review.created_at,
        )


class ProductReviewListParams(PaginationParams):
    pass


class ProductReviewListResponse(StrictSchema):
    items: list[AdminProductReviewResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class CategoryAttributeResponse(StrictSchema):
    id: UUID
    attribute: CatalogAttributeResponse
    is_required: bool
    is_primary_filter: bool
    position: int


class CreateProductRequest(StrictSchema):
    category_id: UUID
    subcategory_id: UUID | None = None
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=2, max_length=240)
    brand: str = Field(min_length=1, max_length=120)
    brand_country: str | None = Field(default=None, max_length=120)
    production_country: str | None = Field(default=None, max_length=120)
    short_description: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=12000)
    image_url: str | None = Field(default=None, max_length=500)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    old_price: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )
    badge: ProductBadge | None = None
    stock_status: StockStatus = StockStatus.IN_STOCK
    availability_days: int | None = Field(default=None, ge=0, le=365)
    sale_unit: SaleUnit = SaleUnit.PIECE
    wholesale_price: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )
    wholesale_min_quantity: int | None = Field(default=None, ge=1, le=100000)
    media: list[ProductMediaInput] = Field(default_factory=list, max_length=20)
    documents: list[ProductDocumentInput] = Field(default_factory=list, max_length=20)
    relations: list[ProductRelationInput] = Field(default_factory=list, max_length=30)
    specs: dict[str, str] = Field(default_factory=dict, max_length=30)

    @field_validator("sku", mode="before")
    @classmethod
    def validate_sku(cls, value: object) -> str:
        return normalize_sku(value)

    @field_validator(
        "name",
        "brand",
        "brand_country",
        "production_country",
        "short_description",
        "description",
        mode="before",
    )
    @classmethod
    def normalize_required_text(cls, value: object) -> str:
        return normalize_text(value)

    @field_validator("image_url", mode="before")
    @classmethod
    def validate_image_url(cls, value: object | None) -> str | None:
        return normalize_image_url(value)

    @field_validator("specs", mode="before")
    @classmethod
    def validate_specs(cls, value: object) -> dict[str, str]:
        return normalize_product_specs(value)

    @model_validator(mode="after")
    def validate_old_price(self) -> "CreateProductRequest":
        if self.old_price is not None and self.old_price < self.price:
            raise ValueError("old_price cannot be lower than price")
        if (self.wholesale_price is None) != (self.wholesale_min_quantity is None):
            raise ValueError(
                "wholesale_price and wholesale_min_quantity must be provided together"
            )
        if self.wholesale_price is not None and self.wholesale_price >= self.price:
            raise ValueError("wholesale_price must be lower than retail price")
        self._validate_positions()
        return self

    def _validate_positions(self) -> None:
        for items, label in ((self.media, "media"), (self.documents, "documents")):
            positions = [item.position for item in items]
            if len(positions) != len(set(positions)):
                raise ValueError(f"{label} positions must be unique")
        relation_keys = [(item.product_id, item.kind) for item in self.relations]
        if len(relation_keys) != len(set(relation_keys)):
            raise ValueError("Product relations must be unique by product and kind")


class UpdateProductRequest(StrictSchema):
    category_id: UUID | None = None
    subcategory_id: UUID | None = None
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=2, max_length=240)
    brand: str | None = Field(default=None, min_length=1, max_length=120)
    brand_country: str | None = Field(default=None, max_length=120)
    production_country: str | None = Field(default=None, max_length=120)
    short_description: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=12000)
    image_url: str | None = Field(default=None, max_length=500)
    price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    old_price: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )
    badge: ProductBadge | None = None
    stock_status: StockStatus | None = None
    availability_days: int | None = Field(default=None, ge=0, le=365)
    sale_unit: SaleUnit | None = None
    wholesale_price: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )
    wholesale_min_quantity: int | None = Field(default=None, ge=1, le=100000)
    media: list[ProductMediaInput] | None = Field(default=None, max_length=20)
    documents: list[ProductDocumentInput] | None = Field(default=None, max_length=20)
    relations: list[ProductRelationInput] | None = Field(default=None, max_length=30)
    specs: dict[str, str] | None = Field(default=None, max_length=30)

    @field_validator("sku", mode="before")
    @classmethod
    def validate_sku(cls, value: object | None) -> str | None:
        return normalize_sku(value) if value is not None else None

    @field_validator(
        "name",
        "brand",
        "brand_country",
        "production_country",
        "short_description",
        "description",
        mode="before",
    )
    @classmethod
    def normalize_required_text(cls, value: object | None) -> str | None:
        return normalize_text(value) if value is not None else None

    @field_validator("image_url", mode="before")
    @classmethod
    def validate_image_url(cls, value: object | None) -> str | None:
        return normalize_image_url(value)

    @field_validator("specs", mode="before")
    @classmethod
    def validate_specs(cls, value: object | None) -> dict[str, str] | None:
        return normalize_product_specs(value) if value is not None else None

    @model_validator(mode="after")
    def require_update(self) -> "UpdateProductRequest":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        required_fields = {
            "category_id": self.category_id,
            "sku": self.sku,
            "name": self.name,
            "brand": self.brand,
            "price": self.price,
            "stock_status": self.stock_status,
            "sale_unit": self.sale_unit,
            "specs": self.specs,
        }
        for field, value in required_fields.items():
            if field in self.model_fields_set and value is None:
                raise ValueError(f"{field} cannot be null")
        if (
            self.price is not None
            and self.old_price is not None
            and self.old_price < self.price
        ):
            raise ValueError("old_price cannot be lower than price")
        for items, label in ((self.media, "media"), (self.documents, "documents")):
            if items is not None:
                positions = [item.position for item in items]
                if len(positions) != len(set(positions)):
                    raise ValueError(f"{label} positions must be unique")
        if self.relations is not None:
            relation_keys = [(item.product_id, item.kind) for item in self.relations]
            if len(relation_keys) != len(set(relation_keys)):
                raise ValueError("Product relations must be unique by product and kind")
        return self
