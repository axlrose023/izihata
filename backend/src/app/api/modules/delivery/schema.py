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
