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

from app.api.modules.catalog.enums import ProductBadge, StockStatus
from app.database.base import Base, DateTimeMixin, UUIDIDMixin


class Category(Base, UUIDIDMixin, DateTimeMixin):
    __tablename__ = "categories"

    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    accent: Mapped[str] = mapped_column(String(24), default="slate")
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

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
    rating: Mapped[Decimal] = mapped_column(Numeric(2, 1), default=Decimal("0"))
    reviews_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

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

    product: Mapped[Product] = relationship(back_populates="attributes")


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
    rating: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    product: Mapped[Product] = relationship(back_populates="reviews")
