"""Run events: persisted to SQLite and fanned out to live listeners (SSE queues, CLI printer)."""

import time
from collections.abc import Callable

from bumpless.storage import db

Listener = Callable[[str, str, dict], None]
_listeners: list[Listener] = []


def add_listener(fn: Listener) -> None:
    _listeners.append(fn)


def remove_listener(fn: Listener) -> None:
    if fn in _listeners:
        _listeners.remove(fn)


def emit(run_id: str | None, type: str, data: dict) -> None:
    db.insert("events", {"run_id": run_id, "ts": time.time(), "type": type, "data_json": data})
    for fn in list(_listeners):
        fn(run_id, type, data)
