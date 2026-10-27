"""Run events: persisted to SQLite and fanned out to live listeners (SSE queues, CLI printer).

A listener receives one dict: {"id", "run_id", "ts", "type", "data"}; `id` is the SQLite row id, so a
stream can replay history and then continue live without gaps or duplicates.
"""

import time
from collections.abc import Callable

from bumpless.storage import db

Listener = Callable[[dict], None]
_listeners: list[Listener] = []


def add_listener(fn: Listener) -> None:
    _listeners.append(fn)


def remove_listener(fn: Listener) -> None:
    if fn in _listeners:
        _listeners.remove(fn)


def emit(run_id: str | None, type: str, data: dict) -> dict:
    ts = time.time()
    eid = db.insert("events", {"run_id": run_id, "ts": ts, "type": type, "data_json": data})
    event = {"id": eid, "run_id": run_id, "ts": ts, "type": type, "data": data}
    for fn in list(_listeners):  # copy: a listener may remove itself
        fn(event)
    return event
