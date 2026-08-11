import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, DateTimeMixin, UUIDIDMixin


class Promotion(Base, UUIDIDMixin, DateTimeMixin):
    __tablename__ = "promotions"
    __table_args__ = (
        CheckConstraint(
            "discount_rate > 0 AND discount_rate <= 1",
            name="promotion_discount_rate_range",
        ),
    )

    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    discount_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    starts_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
