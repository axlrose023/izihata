import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, DateTimeMixin, UUIDIDMixin


class AuthSession(Base, UUIDIDMixin, DateTimeMixin):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        Index("auth_sessions_user_active_idx", "user_id", "revoked_at", "expires_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    refresh_jti: Mapped[UUID] = mapped_column(unique=True)
    expires_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )
