from decimal import Decimal
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.api.modules.orders.models import Order
from app.api.modules.payments.enums import PaymentAttemptStatus
from app.database.base import Base, DateTimeMixin, UUIDIDMixin


class PaymentAttempt(Base, UUIDIDMixin, DateTimeMixin):
    __tablename__ = "payment_attempts"
    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(32), default="wayforpay")
    order_reference: Mapped[str] = mapped_column(String(64), unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="UAH")
    status: Mapped[PaymentAttemptStatus] = mapped_column(
        Enum(
            PaymentAttemptStatus,
            native_enum=False,
            length=24,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=PaymentAttemptStatus.PENDING,
    )
    order: Mapped[Order] = relationship(lazy="raise")
