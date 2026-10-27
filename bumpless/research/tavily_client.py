"""Tavily wrapper: search / extract / map with a 24h SQLite cache and per-call logging."""

import hashlib
import json
import time

from tavily import AsyncTavilyClient

from bumpless import events
from bumpless.settings import settings
from bumpless.storage import db

CACHE_TTL_S = 24 * 3600


def _cache_get(key: str):
    rows = db.query("SELECT ts, data_json FROM tavily_cache WHERE key=?", (key,))
    if rows and time.time() - rows[0]["ts"] < CACHE_TTL_S:
        return json.loads(rows[0]["data_json"])
    return None


def _cache_put(key: str, data) -> None:
    with db.connect() as conn:
        conn.execute("INSERT OR REPLACE INTO tavily_cache VALUES (?, ?, ?)", (key, time.time(), json.dumps(data)))


def _key(kind: str, payload) -> str:
    return kind + ":" + hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


class Tavily:
    def __init__(self, run_id: str | None = None, api_key: str | None = None):
        key = api_key or settings.tavily_api_key
        if not key:
            raise RuntimeError("TAVILY_API_KEY is not set (get one at app.tavily.com)")
        self.client = AsyncTavilyClient(api_key=key)
        self.run_id = run_id
        self.calls: list[dict] = []

    def _log(self, kind: str, query: str, urls: list[str], cached: bool) -> None:
        row = {"run_id": self.run_id, "ts": time.time(), "kind": kind, "query": query,
               "n_results": len(urls), "cached": int(cached), "urls_json": urls}
        self.calls.append(row)
        db.insert("tavily_calls", row)
        events.emit(self.run_id, "tavily_call", row)

    async def search(self, query: str, **kw) -> list[dict]:
        """Results: [{url, title, content, raw_content?}]"""
        key = _key("search", {"q": query, **kw})
        data = _cache_get(key)
        cached = data is not None
        if not cached:
            data = (await self.client.search(query, **kw)).get("results", [])
            _cache_put(key, data)
        self._log("search", query, [r["url"] for r in data], cached)
        return data

    async def extract(self, urls: list[str]) -> dict[str, str]:
        """url -> page text. Each URL is cached separately; failed URLs are omitted."""
        out, todo = {}, []
        for u in dict.fromkeys(urls):
            hit = _cache_get(_key("extract", u))
            if hit is not None:
                out[u] = hit
            else:
                todo.append(u)
        for i in range(0, len(todo), 20):  # API limit: 20 URLs per call
            batch = todo[i:i + 20]
            resp = await self.client.extract(urls=batch, format="markdown")
            for r in resp.get("results", []):
                out[r["url"]] = r.get("raw_content") or ""
                _cache_put(_key("extract", r["url"]), out[r["url"]])
        self._log("extract", ", ".join(urls)[:500], [u for u in urls if u in out], cached=not todo)
        return out

    async def map(self, url: str, **kw) -> list[str]:
        key = _key("map", {"url": url, **kw})
        data = _cache_get(key)
        cached = data is not None
        if not cached:
            data = (await self.client.map(url, **kw)).get("results", [])
            _cache_put(key, data)
        self._log("map", url, data, cached)
        return data
