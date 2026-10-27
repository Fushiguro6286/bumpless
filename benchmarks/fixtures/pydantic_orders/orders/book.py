import json

from orders.models import Money, Order, OrderList, parse_orders


def load(raw: str) -> OrderList:
    return OrderList.parse_raw(raw)


def dump(book: OrderList) -> str:
    return book.json()


def add_tag(order: Order, tag: str) -> Order:
    return order.copy(update={"tags": order.tags + [tag.strip().lower()]})


def reprice(money: Money, factor: str) -> Money:
    return money.copy(update={"amount": money.amount * type(money.amount)(factor)})


def order_schema() -> dict:
    return Order.schema()


def from_rows(rows: list) -> list:
    return [o.id for o in parse_orders(rows)]


def summary(order: Order) -> dict:
    data = json.loads(order.json(include={"id", "tags"}))
    data["total"] = str(order.total())
    return data
