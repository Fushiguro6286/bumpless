from typing import List, Optional

from pydantic import BaseModel, Field, validator


class Ticket(BaseModel):
    id: int
    subject: str = Field(..., min_length=3)
    body: str
    tags: List[str] = []
    priority: Optional[int] = None

    @validator("tags", pre=True)
    def split_tags(cls, v):
        return [t.strip() for t in v.split(",")] if isinstance(v, str) else v

    class Config:
        anystr_strip_whitespace = True


def parse_ticket(raw: str) -> Ticket:
    return Ticket.parse_raw(raw)


def to_record(t: Ticket) -> dict:
    return t.dict(exclude_none=True)
