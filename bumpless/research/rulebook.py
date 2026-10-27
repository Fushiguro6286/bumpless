"""Step 2: research breaking changes with Tavily and synthesize a rulebook (Nano summaries -> Super rules)."""

import asyncio
import re
from datetime import UTC, datetime
from urllib.parse import urldefrag, urlparse

from bumpless.llm import prompts
from bumpless.llm.schemas import Rule, Rulebook, RuleDrafts
from bumpless.pipeline.context import RunContext
from bumpless.radar.pypi import is_official, official_sources, project_info

MAX_PAGE_CHARS = 120_000
CHUNK_CHARS = 40_000
MAX_PAGES = 12
MIGRATION_WORDS = re.compile(r"migrat|upgrad|changelog|breaking|release-notes|whats?-new|changes", re.I)


def norm_url(u: str) -> str:
    return urldefrag(u)[0].rstrip("/")


class Sources:
    """Everything we fetched, keyed by normalized URL. Rules may only cite URLs in here."""

    def __init__(self, domains: set[str], repos: list[str]):
        self.domains, self.repos = domains, repos
        self.pages: dict[str, str] = {}

    def add(self, url: str, text: str) -> None:
        if text and len(text) > len(self.pages.get(norm_url(url), "")):
            self.pages[norm_url(url)] = text[:MAX_PAGE_CHARS]

    def official(self, url: str) -> bool:
        return is_official(url, self.domains, self.repos)


async def discover_sources(ctx: RunContext, fm: str, tm: str) -> Sources:
    pkg = ctx.package
    info = await project_info(pkg)
    domains, repos = official_sources(info)
    src = Sources(domains, repos)
    official = sorted(domains) + ["github.com"]
    queries = [
        (f"{pkg} {fm} to {tm} migration guide", official),
        (f"{pkg} {tm}.0 changelog breaking changes removed deprecated", official),
        (f"{pkg} v{tm} upgrade common errors", None),
    ]
    results = await asyncio.gather(*[
        ctx.tavily.search(q, search_depth="advanced", max_results=6, include_raw_content="markdown",
                          **({"include_domains": d} if d else {}))
        for q, d in queries
    ])
    hits = [r for rs in results for r in rs]
    for r in hits:
        src.add(r["url"], r.get("raw_content") or r.get("content") or "")

    # Docs coverage: map the official migration guide's site section and extract the related pages.
    guide = next((r["url"] for r in hits if src.official(r["url"]) and MIGRATION_WORDS.search(r["url"])), None)
    if guide:
        p = urlparse(guide)
        # Map the guide's docs section (e.g. docs.pydantic.dev/latest/), not the bare domain; climb up to
        # two folders if the section is too small to hold the related pages.
        parts = [x for x in p.path.split("/") if x]
        urls: list[str] = []
        for up in (1, 2, 3):
            if up > len(parts):
                break
            section = "/" + "/".join(parts[:-up]) + ("/" if len(parts) > up else "")
            try:
                urls = await ctx.tavily.map(f"{p.scheme}://{p.netloc}{section}", max_depth=3, limit=100,
                                            select_paths=[re.escape(section) + ".*"],
                                            instructions=f"migration guide, breaking changes, changelog for {pkg} {tm}")
            except Exception as e:  # map is a nice-to-have; search results still give us sources
                ctx.progress("research", f"site map failed ({type(e).__name__}); using search results only")
                break
            if len(urls) >= 5:
                break
        related = [u for u in urls if MIGRATION_WORDS.search(u) and norm_url(u) not in src.pages]
        if related:
            for u, text in (await ctx.tavily.extract(related[:MAX_PAGES])).items():
                src.add(u, text)
    return src


async def summarize_pages(ctx: RunContext, src: Sources, fm: str, tm: str) -> dict[str, str]:
    sem = asyncio.Semaphore(6)

    async def one(url: str, chunk: str, escalation: int = 0) -> tuple[str, str]:
        async with sem:
            text = await ctx.llm.chat("summarize", [{"role": "user", "content": prompts.render(
                "summarize", package=ctx.package, url=url, text=chunk, **{"from": fm, "to": tm})}],
                step="research", max_tokens=6000, escalation=escalation)
            return url, text

    def chunks(t: str) -> list[str]:
        return [t[i:i + CHUNK_CHARS] for i in range(0, len(t), CHUNK_CHARS)]

    async def collect(jobs) -> dict[str, str]:
        out: dict[str, str] = {}
        for url, text in await asyncio.gather(*jobs):
            if text.strip() and text.strip().upper() != "NONE":
                out[url] = (out.get(url, "") + "\n" + text).strip()
        return out

    notes = await collect([one(u, c) for u, t in src.pages.items() for c in chunks(t)])
    # Nano sometimes finds nothing on long, oddly formatted official guides: give those a second read by Super.
    missed = [u for u, t in src.pages.items()
              if u not in notes and src.official(u) and MIGRATION_WORDS.search(u + t[:300])]
    if missed:
        ctx.progress("research", f"{len(missed)} official guide page(s) re-read by Super (Nano found nothing)")
        notes |= await collect([one(u, c, 1) for u in missed for c in chunks(src.pages[u])])
    return notes


async def synthesize(ctx: RunContext, src: Sources, notes: dict[str, str], fm: str, tm: str,
                     usage: list[str], max_rules: int = 30) -> list[Rule]:
    blob = "\n\n".join(f"SOURCE: {u}\n{n}" for u, n in notes.items())
    drafts = await ctx.llm.chat("rulebook", [{"role": "user", "content": prompts.render(
        "rulebook", package=ctx.package, usage=", ".join(usage[:80]) or "(unknown)", notes=blob,
        max_rules=max_rules, **{"from": fm, "to": tm})}], step="research", schema=RuleDrafts, max_tokens=12000)
    return keep_cited(drafts.rules, src)


def keep_cited(rules: list[Rule], src: Sources) -> list[Rule]:
    """Drop rules whose source_url is not a page Tavily actually returned; mark official sources."""
    kept = []
    for r in rules:
        url = norm_url(r.source_url)
        if url in src.pages:
            r.source_url = url
            r.source_official = src.official(url)
            kept.append(r)
    return kept


def number_rules(rules: list[Rule], start: int = 1) -> list[Rule]:
    for i, r in enumerate(rules, start):
        r.id = f"R{i:03d}"
    return rules


async def research(ctx: RunContext, usage: list[str]) -> Rulebook:
    fm, tm = ctx.from_major, ctx.to_major
    src = await discover_sources(ctx, fm, tm)
    n_official = sum(src.official(u) for u in src.pages)
    ctx.progress("research", f"Fetched {len(src.pages)} pages ({n_official} official)",
                 pages=[{"url": u, "official": src.official(u)} for u in src.pages])
    notes = await summarize_pages(ctx, src, fm, tm)
    rules = number_rules(await synthesize(ctx, src, notes, fm, tm, usage))
    now = datetime.now(UTC).isoformat(timespec="seconds")
    ctx.sources = src
    return Rulebook(package=ctx.package, from_=fm, to=tm, created_at=now, checked_at=now,
                    official_pages=sum(src.official(u) for u in notes), rules=rules)
