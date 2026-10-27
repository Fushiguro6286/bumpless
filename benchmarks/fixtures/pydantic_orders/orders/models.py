from datetime import datetime
from decimal import Decimal
from typing import List

from pydantic import BaseModel, Field, parse_obj_as, validator


class Money(BaseModel):
    amount: Decimal
    currency: str = "INR"

    class Config:
        allow_mutation = False
        json_encoders = {Decimal: lambda d: str(d.quantize(Decimal("0.01")))}


class Line(BaseModel):
    sku: str
    qty: int = Field(..., gt=0)
    price: Money


class Order(BaseModel):
    id: int
    lines: List[Line] = Field(..., min_items=1)
    tags: List[str] = []
    placed_at: datetime

    @validator("tags", each_item=True)
    def lower_tags(cls, v):
        return v.strip().lower()

    class Config:
        json_encoders = {Decimal: lambda d: str(d.quantize(Decimal("0.01")))}

    def total(self) -> Decimal:
        return sum((ln.price.amount * ln.qty for ln in self.lines), Decimal("0"))


class OrderList(BaseModel):
    __root__: List[Order]

    class Config:
        json_encoders = {Decimal: lambda d: str(d.quantize(Decimal("0.01")))}

    def ids(self) -> List[int]:
        return [o.id for o in self.__root__]


def parse_orders(data: list) -> List[Order]:
    return parse_obj_as(List[Order], data)
