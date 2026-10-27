import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from inventory.api import (
    catalog_from_json,
    catalog_json,
    product_fields,
    product_from_payload,
    product_to_payload,
    reprice,
)
from inventory.catalog import Catalog, Money, Product


def make(**kw):
    data = {"SKU": " ab-1 ", "title": "Lamp", "price": {"amount": "100.00"}}
    data.update(kw)
    return product_from_payload(data)


def test_alias_and_pre_validator():
    p = make()
    assert p.sku == "AB-1"
    assert product_to_payload(p)["SKU"] == "AB-1"


def test_populate_by_field_name():
    p = Product(sku="xyz", title="T", price=Money(amount=Decimal("5")))
    assert p.sku == "XYZ"


def test_money_is_frozen():
    m = Money(amount=Decimal("1"))
    with pytest.raises(TypeError):
        m.amount = Decimal("2")


def test_discount_validation_and_price():
    assert make(discount_pct=10).final_price() == Decimal("90.00")
    with pytest.raises(ValidationError):
        make(discount_pct=95)


def test_tag_limit():
    with pytest.raises(ValidationError):
        make(tags=["a", "b", "c", "d", "e", "f"])


def test_catalog_needs_products():
    with pytest.raises(ValidationError):
        Catalog(name="empty", products=[])


def test_catalog_json_roundtrip():
    c = Catalog(name="main", products=[make()])
    raw = catalog_json(c)
    assert json.loads(raw)["products"][0]["SKU"] == "AB-1"
    assert catalog_from_json(raw) == c


def test_reprice_copies():
    p = make()
    q = reprice(p, 20)
    assert q.discount_pct == 20 and p.discount_pct is None


def test_required_fields():
    assert product_fields() == {"sku": True, "title": True, "price": True, "tags": False, "discount_pct": False}
