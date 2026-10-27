"""Plain sqlite3 storage. One connection per call keeps it thread-safe and simple."""

import json
import sqlite3
from pathlib import Path

from bumpless.settings import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY, created_at REAL, repo TEXT, package TEXT, target TEXT,
    routing TEXT, status TEXT, result_json TEXT
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, ts REAL, type TEXT, data_json TEXT
);
CREATE TABLE IF NOT EXISTS llm_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, ts REAL, step TEXT, task TEXT, tier TEXT,
    model TEXT, prompt_tokens INTEGER, completion_tokens INTEGER, latency_s REAL, cost_usd REAL
);
CREATE INDEX IF NOT EXISTS events_run ON events(run_id);
CREATE INDEX IF NOT EXISTS llm_calls_run ON llm_calls(run_id);
"""


def connect(path: Path | None = None) -> sqlite3.Connection:
    path = path or settings.db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def insert(table: str, row: dict) -> int:
    cols = ", ".join(row)
    marks = ", ".join("?" for _ in row)
    vals = [json.dumps(v) if isinstance(v, (dict, list)) else v for v in row.values()]
    with connect() as conn:
        return conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", vals).lastrowid


def query(sql: str, params: tuple = ()) -> list[dict]:
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
