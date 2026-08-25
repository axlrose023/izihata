from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.api.modules.orders.enums import (
    DeliveryMethod,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
)
from app.database.base import Base, DateTimeMixin, UUIDIDMixin


class Order(Base, UUIDIDMixin, DateTimeMixin):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("subtotal >= 0", name="order_subtotal_non_negative"),
        CheckConstraint("discount >= 0", name="order_discount_non_negative"),
        CheckConstraint("total >= 0", name="order_total_non_negative"),
        Index("orders_created_at_idx", "created_at"),
    )

    number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    customer_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"),
        index=True,
    )
    customer_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(24), index=True)
    company_name: Mapped[str | None] = mapped_column(String(180))
    edrpou: Mapped[str | None] = mapped_column(String(10))
    delivery_method: Mapped[DeliveryMethod] = mapped_column(
        Enum(DeliveryMethod, native_enum=False, length=32)
    )
    delivery_city: Mapped[str | None] = mapped_column(String(120))
    delivery_point: Mapped[str | None] = mapped_column(String(200))
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, native_enum=False, length=32)
    )
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, native_enum=False, length=24),
        index=True,
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, native_enum=False, length=24),
        default=OrderStatus.NEW,
        index=True,
    )
    promo_code: Mapped[str | None] = mapped_column(String(64))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderItem.id",
        lazy="raise",
    )


class OrderItem(Base, UUIDIDMixin):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="order_item_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="order_item_price_non_negative"),
        CheckConstraint("total >= 0", name="order_item_total_non_negative"),
    )

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        index=True,
    )
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"),
        index=True,
    )
    sku: Mapped[str] = mapped_column(String(64))
    product_name: Mapped[str] = mapped_column(String(240))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    order: Mapped[Order] = relationship(back_populates="items")
