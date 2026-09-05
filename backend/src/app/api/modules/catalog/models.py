from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.api.modules.catalog.enums import (
    AttributeValueType,
    ProductBadge,
    ProductDocumentKind,
    ProductRelationKind,
    ReviewStatus,
    SaleUnit,
    StockStatus,
    StockSubscriptionStatus,
)
from app.database.base import Base, DateTimeMixin, UUIDIDMixin


class CatalogSection(Base, UUIDIDMixin, DateTimeMixin):
    __tablename__ = "catalog_sections"

    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(500))
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    categories: Mapped[list["Category"]] = relationship(
        back_populates="section",
        order_by="Category.position",
        lazy="raise",
    )


class Category(Base, UUIDIDMixin, DateTimeMixin):
    __tablename__ = "categories"

    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    accent: Mapped[str] = mapped_column(String(24), default="slate")
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    section_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("catalog_sections.id", ondelete="RESTRICT"),
        index=True,
    )

    section: Mapped[CatalogSection | None] = relationship(back_populates="categories")
    subcategories: Mapped[list["Subcategory"]] = relationship(
        back_populates="category",
        order_by="Subcategory.position",
        lazy="raise",
    )


class Subcategory(Base, UUIDIDMixin, DateTimeMixin):
    __tablename__ = "subcategories"
    __table_args__ = (
        UniqueConstraint("category_id", "slug", name="subcategory_category_slug_ukey"),
    )

    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(96), index=True)
    name: Mapped[str] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    category: Mapped[Category] = relationship(back_populates="subcategories")


class Product(Base, UUIDIDMixin, DateTimeMixin):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price >= 0", name="product_price_non_negative"),
        CheckConstraint(
            "old_price IS NULL OR old_price >= price",
            name="product_old_price_valid",
        ),
        CheckConstraint(
            "rating >= 0 AND rating <= 5",
            name="product_rating_range",
        ),
        CheckConstraint(
            "reviews_count >= 0",
            name="product_reviews_count_non_negative",
        ),
        CheckConstraint(
            "wholesale_price IS NULL OR wholesale_price >= 0",
            name="product_wholesale_price_non_negative",
        ),
        CheckConstraint(
            "wholesale_min_quantity IS NULL OR wholesale_min_quantity > 0",
            name="product_wholesale_min_quantity_positive",
        ),
        Index(
            "products_name_trgm_idx",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )

    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        index=True,
    )
    subcategory_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("subcategories.id", ondelete="SET NULL"),
        index=True,
    )
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(240), index=True)
    brand: Mapped[str] = mapped_column(String(120), index=True)
    brand_country: Mapped[str | None] = mapped_column(String(120))
    production_country: Mapped[str | None] = mapped_column(String(120))
    short_description: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(500))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    old_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    badge: Mapped[ProductBadge | None] = mapped_column(
        Enum(ProductBadge, native_enum=False, length=16),
    )
    stock_status: Mapped[StockStatus] = mapped_column(
        Enum(StockStatus, native_enum=False, length=24),
        default=StockStatus.IN_STOCK,
        index=True,
    )
    availability_days: Mapped[int | None] = mapped_column(Integer)
    sale_unit: Mapped[SaleUnit] = mapped_column(
        Enum(SaleUnit, native_enum=False, length=16),
        default=SaleUnit.PIECE,
        nullable=False,
    )
    wholesale_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    wholesale_min_quantity: Mapped[int | None] = mapped_column(Integer)
    rating: Mapped[Decimal] = mapped_column(Numeric(2, 1), default=Decimal("0"))
    reviews_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    # Editorial pick, independent of ``badge`` so a product can be both
    # popular and discounted at the same time.
    is_popular: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    category: Mapped[Category] = relationship(lazy="raise")
    subcategory: Mapped[Subcategory | None] = relationship(lazy="raise")
    attributes: Mapped[list["ProductAttribute"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductAttribute.key",
        lazy="raise",
    )
    reviews: Mapped[list["ProductReview"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductReview.created_at.desc()",
        lazy="raise",
    )
    media: Mapped[list["ProductMedia"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductMedia.position",
        lazy="raise",
    )
    documents: Mapped[list["ProductDocument"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductDocument.position",
        lazy="raise",
    )


class ProductAttribute(Base, UUIDIDMixin):
    __tablename__ = "product_attributes"
    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "key",
            name="product_attribute_product_key_ukey",
        ),
        Index("product_attributes_key_value_idx", "key", "value"),
    )

    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        index=True,
    )
    key: Mapped[str] = mapped_column(String(120), index=True)
    value: Mapped[str] = mapped_column(String(160), index=True)
    attribute_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("catalog_attributes.id", ondelete="SET NULL"),
        index=True,
    )
    numeric_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))

    product: Mapped[Product] = relationship(back_populates="attributes")
    attribute: Mapped["CatalogAttribute | None"] = relationship()


class CatalogAttribute(Base, UUIDIDMixin, DateTimeMixin):
    __tablename__ = "catalog_attributes"

    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    value_type: Mapped[AttributeValueType] = mapped_column(
        Enum(AttributeValueType, native_enum=False, length=16),
        default=AttributeValueType.SELECT,
        nullable=False,
    )
    unit: Mapped[str | None] = mapped_column(String(32))
    is_filterable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class CategoryAttribute(Base, UUIDIDMixin):
    __tablename__ = "category_attributes"
    __table_args__ = (
        UniqueConstraint(
            "category_id",
            "attribute_id",
            name="category_attribute_category_attribute_ukey",
        ),
    )

    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"),
        index=True,
    )
    attribute_id: Mapped[UUID] = mapped_column(
        ForeignKey("catalog_attributes.id", ondelete="CASCADE"),
        index=True,
    )
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_primary_filter: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ProductMedia(Base, UUIDIDMixin, DateTimeMixin):
    __tablename__ = "product_media"
    __table_args__ = (
        UniqueConstraint("product_id", "position", name="product_media_position_ukey"),
    )

    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        index=True,
    )
    url: Mapped[str] = mapped_column(String(500))
    alt: Mapped[str] = mapped_column(String(240))
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    product: Mapped[Product] = relationship(back_populates="media")


class ProductDocument(Base, UUIDIDMixin, DateTimeMixin):
    __tablename__ = "product_documents"
    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "position",
            name="product_document_position_ukey",
        ),
    )

    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        index=True,
    )
    kind: Mapped[ProductDocumentKind] = mapped_column(
        Enum(ProductDocumentKind, native_enum=False, length=16),
        default=ProductDocumentKind.CERTIFICATE,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(240))
    url: Mapped[str] = mapped_column(String(500))
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    product: Mapped[Product] = relationship(back_populates="documents")


class ProductRelation(Base, UUIDIDMixin, DateTimeMixin):
    __tablename__ = "product_relations"
    __table_args__ = (
        UniqueConstraint(
            "source_product_id",
            "target_product_id",
            "kind",
            name="product_relation_identity_ukey",
        ),
        CheckConstraint(
            "source_product_id <> target_product_id",
            name="product_relation_distinct_products",
        ),
    )

    source_product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        index=True,
    )
    target_product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        index=True,
    )
    kind: Mapped[ProductRelationKind] = mapped_column(
        Enum(ProductRelationKind, native_enum=False, length=24),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ProductStockSubscription(Base, UUIDIDMixin, DateTimeMixin):
    __tablename__ = "product_stock_subscriptions"
    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "email",
            name="product_stock_subscription_product_email_ukey",
        ),
    )

    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        index=True,
    )
    email: Mapped[str] = mapped_column(String(254))
    status: Mapped[StockSubscriptionStatus] = mapped_column(
        Enum(StockSubscriptionStatus, native_enum=False, length=16),
        default=StockSubscriptionStatus.ACTIVE,
        index=True,
    )


class ProductReview(Base, UUIDIDMixin, DateTimeMixin):
    __tablename__ = "product_reviews"
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="review_rating_range"),
    )

    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        index=True,
    )
    author: Mapped[str] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(254))
    rating: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, native_enum=False, length=16),
        default=ReviewStatus.PUBLISHED,
        index=True,
    )

    product: Mapped[Product] = relationship(back_populates="reviews")
