from uuid import UUID

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.api.modules.leads.enums import LeadStatus, LeadType
from app.database.base import Base, DateTimeMixin, UUIDIDMixin


class Lead(Base, UUIDIDMixin, DateTimeMixin):
    __tablename__ = "leads"

    type: Mapped[LeadType] = mapped_column(
        Enum(LeadType, native_enum=False, length=24),
        index=True,
    )
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus, native_enum=False, length=24),
        default=LeadStatus.NEW,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(24), index=True)
    company: Mapped[str | None] = mapped_column(String(180))
    product_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"),
        index=True,
    )
