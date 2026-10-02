from pydantic import BaseModel, ConfigDict, Field

from app.settings import get_config

config = get_config()


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class PaginationParams(StrictSchema):
    # Keep every allowed page size within the signed BIGINT SQL OFFSET range.
    page: int = Field(1, ge=1, le=((1 << 63) - 1) // config.api.page_max_size + 1)
    page_size: int = Field(
        config.api.page_default_size, ge=1, le=config.api.page_max_size
    )

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
