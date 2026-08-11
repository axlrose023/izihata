from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.api.common.schema import PaginationParams, StrictSchema
from app.api.common.utils import normalize_optional_text, normalize_text
from app.api.modules.catalog.enums import ProductBadge, ProductSort, StockStatus
from app.api.modules.catalog.models import Product, ProductReview
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


class ProductResponse(StrictSchema):
    id: UUID
    sku: str
    slug: str
    name: str
    brand: str
    image_url: str | None
    price: Decimal
    old_price: Decimal | None
    badge: ProductBadge | None
    stock_status: StockStatus
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
            image_url=product.image_url,
            price=product.price,
            old_price=product.old_price,
            badge=product.badge,
            stock_status=product.stock_status,
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
    reviews: list[ProductReviewResponse]

    @classmethod
    def from_product(cls, product: Product) -> "ProductDetailResponse":
        summary = ProductResponse.from_product(product)
        return cls(
            **summary.model_dump(),
            reviews=[
                ProductReviewResponse.from_review(review)
                for review in product.reviews
                if review.is_published
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
    price: PriceFacet


class ProductListParams(PaginationParams):
    product_ids: list[UUID] = Field(
        default_factory=list,
        alias="id",
        max_length=100,
    )
    search: str | None = Field(default=None, min_length=2, max_length=120)
    category: str | None = Field(default=None, min_length=1, max_length=64)
    subcategory: str | None = Field(default=None, min_length=1, max_length=96)
    brand: list[str] = Field(default_factory=list)
    in_stock: bool = False
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, ge=0)
    spec: list[str] = Field(default_factory=list)
    sort: ProductSort = ProductSort.POPULAR

    @field_validator("product_ids")
    @classmethod
    def validate_product_ids(cls, values: list[UUID]) -> list[UUID]:
        return list(dict.fromkeys(values))

    @field_validator("search", "category", "subcategory", mode="before")
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


class CreateProductRequest(StrictSchema):
    category_id: UUID
    subcategory_id: UUID | None = None
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=2, max_length=240)
    brand: str = Field(min_length=1, max_length=120)
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
    specs: dict[str, str] = Field(default_factory=dict, max_length=30)

    @field_validator("sku", mode="before")
    @classmethod
    def validate_sku(cls, value: object) -> str:
        return normalize_sku(value)

    @field_validator("name", "brand", mode="before")
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
        return self


class UpdateProductRequest(StrictSchema):
    category_id: UUID | None = None
    subcategory_id: UUID | None = None
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=2, max_length=240)
    brand: str | None = Field(default=None, min_length=1, max_length=120)
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
    specs: dict[str, str] | None = Field(default=None, max_length=30)

    @field_validator("sku", mode="before")
    @classmethod
    def validate_sku(cls, value: object | None) -> str | None:
        return normalize_sku(value) if value is not None else None

    @field_validator("name", "brand", mode="before")
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
        return self
