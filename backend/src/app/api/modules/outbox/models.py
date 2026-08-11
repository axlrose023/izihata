import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, DateTimeMixin, UUIDIDMixin


class OutboxStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    DEAD = "dead"


class OutboxEvent(Base, UUIDIDMixin, DateTimeMixin):
    __tablename__ = "outbox_events"
    __table_args__ = (
        Index(
            "ix_outbox_events_dispatch",
            "status",
            "next_attempt_at",
            "locked_until",
            "created_at",
        ),
    )

    topic: Mapped[str] = mapped_column(String(80), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[OutboxStatus] = mapped_column(
        Enum(OutboxStatus, native_enum=False, length=16),
        default=OutboxStatus.PENDING,
        index=True,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_attempt_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )
    locked_until: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )
    processed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    last_error: Mapped[str | None] = mapped_column(Text)
