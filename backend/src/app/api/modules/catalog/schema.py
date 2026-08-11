from decimal import Decimal
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.api.common.schema import PaginationParams, StrictSchema
from app.api.common.utils import normalize_optional_text
from app.api.modules.catalog.enums import ProductBadge, ProductSort, StockStatus
from app.api.modules.catalog.models import Product


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


class UpdateProductRequest(StrictSchema):
    price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    old_price: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )
    stock_status: StockStatus | None = None

    @model_validator(mode="after")
    def require_update(self) -> "UpdateProductRequest":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if "price" in self.model_fields_set and self.price is None:
            raise ValueError("price cannot be null")
        if "stock_status" in self.model_fields_set and self.stock_status is None:
            raise ValueError("stock_status cannot be null")
        if (
            self.price is not None
            and self.old_price is not None
            and self.old_price < self.price
        ):
            raise ValueError("old_price cannot be lower than price")
        return self
