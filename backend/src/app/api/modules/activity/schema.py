from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator

from app.api.common.schema import PaginationParams, StrictSchema
from app.api.modules.activity.models import SiteVisitor


class TrackVisitRequest(StrictSchema):
    path: str = Field(min_length=1, max_length=500)

    @field_validator("path", mode="before")
    @classmethod
    def normalize_path(cls, value: object) -> str:
        path = str(value or "/").strip()
        return path if path.startswith("/") else "/"


class VisitorResponse(StrictSchema):
    id: UUID
    first_seen_at: datetime
    last_seen_at: datetime
    page_views: int
    orders_count: int
    leads_count: int
    last_path: str | None
    name: str | None
    phone: str | None
    customer_id: UUID | None
    is_registered: bool

    @classmethod
    def from_visitor(cls, visitor: SiteVisitor) -> "VisitorResponse":
        return cls(
            id=visitor.id,
            first_seen_at=visitor.first_seen_at,
            last_seen_at=visitor.last_seen_at,
            page_views=visitor.page_views,
            orders_count=visitor.orders_count,
            leads_count=visitor.leads_count,
            last_path=visitor.last_path,
            name=visitor.name,
            phone=visitor.phone,
            customer_id=visitor.customer_id,
            is_registered=visitor.customer_id is not None,
        )

    model_config = ConfigDict(extra="forbid", from_attributes=True)


class VisitorListParams(PaginationParams):
    search: str | None = Field(default=None, min_length=2, max_length=120)
    with_contacts: bool = False

    @field_validator("search", mode="before")
    @classmethod
    def normalize_search(cls, value: object | None) -> str | None:
        text = str(value).strip() if value is not None else None
        return text or None


class VisitorListResponse(StrictSchema):
    items: list[VisitorResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
