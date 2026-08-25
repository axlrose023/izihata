from decimal import Decimal

from sqlalchemy import Enum, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.api.modules.custom_boards.enums import BoardApplication, BoardRequestStatus
from app.database.base import Base, DateTimeMixin, UUIDIDMixin


class CustomBoardRequest(Base, UUIDIDMixin, DateTimeMixin):
    __tablename__ = "custom_board_requests"

    customer_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(24), index=True)
    email: Mapped[str | None] = mapped_column(String(254))
    application: Mapped[BoardApplication] = mapped_column(
        Enum(BoardApplication, native_enum=False, length=16),
        nullable=False,
    )
    groups_count: Mapped[int] = mapped_column(Integer)
    ip_class: Mapped[str] = mapped_column(String(16))
    automation_brand: Mapped[str | None] = mapped_column(String(120))
    budget: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    details: Mapped[str | None] = mapped_column(Text)
    estimated_from_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[BoardRequestStatus] = mapped_column(
        Enum(BoardRequestStatus, native_enum=False, length=16),
        default=BoardRequestStatus.NEW,
        index=True,
    )


class CustomBoardPortfolioItem(Base, UUIDIDMixin, DateTimeMixin):
    __tablename__ = "custom_board_portfolio_items"

    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str] = mapped_column(String(500))
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
