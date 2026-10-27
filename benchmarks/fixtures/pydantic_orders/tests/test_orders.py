import json
from decimal import Decimal

import pytest

from orders.book import add_tag, dump, from_rows, load, order_schema, reprice, summary
from orders.models import Money, Order

ROW = {"id": 7, "lines": [{"sku": "A1", "qty": 2, "price": {"amount": "10.5"}}], "tags": [" Rush "],
       "placed_at": "2024-01-02T03:04:05"}


def test_parse_and_total():
    o = Order.parse_obj(ROW)
    assert o.tags == ["rush"]
    assert o.total() == Decimal("21.0")


def test_lines_required():
    with pytest.raises(ValueError):
        Order.parse_obj({**ROW, "lines": []})


def test_money_is_immutable():
    m = Money(amount=Decimal("1"))
    with pytest.raises(TypeError):
        m.amount = Decimal("2")


def test_root_list_roundtrip():
    raw = json.dumps([ROW, {**ROW, "id": 8}])
    book = load(raw)
    assert book.ids() == [7, 8]
    again = json.loads(dump(book))
    assert again[1]["id"] == 8 and again[0]["lines"][0]["price"]["amount"] == "10.50"


def test_add_tag_returns_copy():
    o = Order.parse_obj(ROW)
    o2 = add_tag(o, " VIP")
    assert o2.tags == ["rush", "vip"] and o.tags == ["rush"]


def test_reprice():
    assert reprice(Money(amount=Decimal("10")), "1.5").amount == Decimal("15.0")


def test_schema_mentions_fields():
    s = order_schema()
    assert s["title"] == "Order" and set(s["required"]) == {"id", "lines", "placed_at"}


def test_from_rows():
    assert from_rows([ROW, {**ROW, "id": 9}]) == [7, 9]


def test_summary():
    assert summary(Order.parse_obj(ROW)) == {"id": 7, "tags": ["rush"], "total": "21.0"}
