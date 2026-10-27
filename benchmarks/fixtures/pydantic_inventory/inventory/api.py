from typing import Any, Dict

from inventory.catalog import Catalog, Product


def product_from_payload(payload: Dict[str, Any]) -> Product:
    return Product.parse_obj(payload)


def product_to_payload(p: Product) -> Dict[str, Any]:
    return p.dict(by_alias=True, exclude_none=True)


def catalog_json(c: Catalog) -> str:
    return c.json(by_alias=True)


def catalog_from_json(raw: str) -> Catalog:
    return Catalog.parse_raw(raw)


def reprice(p: Product, pct: int) -> Product:
    return p.copy(update={"discount_pct": pct})


def product_fields() -> Dict[str, bool]:
    return {name: f.required for name, f in Product.__fields__.items()}
