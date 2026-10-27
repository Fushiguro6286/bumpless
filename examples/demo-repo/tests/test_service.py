from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models import Address, User, UserUpdate
from app.service import (
    UserRow,
    apply_update,
    field_names,
    parse_user_json,
    parse_users,
    roundtrip,
    to_json,
    to_payload,
    user_from_row,
)

NOW = datetime(2024, 1, 2, 3, 4, 5)


def make_user(**kw):
    data = dict(id=1, name="  Asha  ", email="ASHA@Example.com", created_at=NOW)
    data.update(kw)
    return User(**data)


def test_strips_whitespace_and_lowercases_email():
    u = make_user()
    assert u.name == "Asha"
    assert u.email == "asha@example.com"


def test_invalid_email_rejected():
    with pytest.raises(ValidationError):
        make_user(email="nope")


def test_negative_age_rejected():
    with pytest.raises(ValidationError):
        make_user(age=-1)


def test_zip_code_pattern():
    Address(street="1 Main", city="X", zip_code="12345")
    with pytest.raises(ValidationError):
        Address(street="1 Main", city="X", zip_code="12")


def test_from_orm_row():
    row = UserRow(id=7, name="Ravi", email="r@x.io", age=30, tags=["a"], address=None, created_at=NOW)
    assert user_from_row(row).id == 7


def test_payload_excludes_none():
    payload = to_payload(make_user())
    assert "age" not in payload
    assert payload["tags"] == []


def test_json_roundtrip():
    u = make_user(address=Address(street="1 Main", city="X", zip_code="12345"))
    assert roundtrip(u) == u
    assert parse_user_json(to_json(u)) == u


def test_parse_users():
    users = parse_users([{"id": 1, "name": "a", "email": "a@b.c", "created_at": "2024-01-01T00:00:00"}])
    assert users[0].created_at.year == 2024


def test_partial_update():
    u = make_user(tags=["x"])
    updated = apply_update(u, UserUpdate(name="New"))
    assert updated.name == "New"
    assert updated.tags == ["x"]


def test_update_fields_optional():
    assert UserUpdate().name is None


def test_field_names():
    assert field_names() == ["id", "name", "email", "age", "tags", "address", "created_at"]
