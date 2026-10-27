from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class Money(BaseModel):
    amount: Decimal
    currency: str = "INR"

    class Config:
        allow_mutation = False


class Product(BaseModel):
    sku: str = Field(..., alias="SKU", min_length=3)
    title: str
    price: Money
    tags: List[str] = Field(default_factory=list, max_items=5)
    discount_pct: Optional[int] = None

    class Config:
        allow_population_by_field_name = True

    @validator("sku", pre=True)
    def upper_sku(cls, v):
        return str(v).strip().upper()

    @validator("discount_pct")
    def discount_range(cls, v):
        if v is not None and not 0 <= v <= 90:
            raise ValueError("discount must be 0-90")
        return v

    def final_price(self) -> Decimal:
        pct = self.discount_pct or 0
        return (self.price.amount * (100 - pct) / 100).quantize(Decimal("0.01"))


class Catalog(BaseModel):
    name: str
    products: List[Product] = Field(..., min_items=1)
