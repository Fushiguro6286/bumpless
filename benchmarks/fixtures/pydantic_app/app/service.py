import json
from typing import Any, Dict, List

from app.models import User, UserUpdate


class UserRow:
    """Stand-in for an ORM row object."""

    def __init__(self, **kw: Any) -> None:
        self.__dict__.update(kw)


def user_from_row(row: UserRow) -> User:
    return User.from_orm(row)


def to_payload(user: User) -> Dict[str, Any]:
    return user.dict(exclude_none=True)


def to_json(user: User) -> str:
    return user.json()


def parse_users(data: List[Dict[str, Any]]) -> List[User]:
    return [User.parse_obj(d) for d in data]


def parse_user_json(raw: str) -> User:
    return User.parse_raw(raw)


def apply_update(user: User, update: UserUpdate) -> User:
    return user.copy(update=update.dict(exclude_unset=True))


def field_names() -> List[str]:
    return list(User.__fields__.keys())


def roundtrip(user: User) -> User:
    return User.parse_obj(json.loads(user.json()))
