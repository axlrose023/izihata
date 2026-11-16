from pydantic import BaseModel


class DeliveryCityResponse(BaseModel):
    ref: str
    name: str
    label: str


class DeliveryPointResponse(BaseModel):
    ref: str
    name: str
    label: str
    number: str


class DeliveryPointPage(BaseModel):
    items: list[DeliveryPointResponse]
    next_page: int | None
