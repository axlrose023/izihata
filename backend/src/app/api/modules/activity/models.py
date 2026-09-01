import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, DateTimeMixin, UUIDIDMixin


class SiteVisitor(Base, UUIDIDMixin, DateTimeMixin):
    """One browser, identified by a first-party cookie.

    Guests are tracked too, so staff can follow up on an abandoned basket.
    Contact details are copied here only once a visitor leaves them in a lead
    or an order — browsing alone never produces a name or a phone number.
    """

    __tablename__ = "site_visitors"
    __table_args__ = (
        CheckConstraint("page_views >= 0", name="site_visitor_page_views_valid"),
        CheckConstraint("orders_count >= 0", name="site_visitor_orders_count_valid"),
        CheckConstraint("leads_count >= 0", name="site_visitor_leads_count_valid"),
        Index("site_visitors_last_seen_at_idx", "last_seen_at"),
    )

    visitor_key: Mapped[UUID] = mapped_column(unique=True, index=True)
    first_seen_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_seen_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    page_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    orders_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    leads_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_path: Mapped[str | None] = mapped_column(String(500))
    user_agent: Mapped[str | None] = mapped_column(String(400))
    customer_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"),
        index=True,
    )
    name: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(24), index=True)
