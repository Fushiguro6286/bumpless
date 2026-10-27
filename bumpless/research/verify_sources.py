"""Step 2.5: every rule is checked against the text of the page it cites. Unverified rules are never applied."""

import asyncio
import re

from pydantic import BaseModel

from bumpless.llm import prompts
from bumpless.llm.client import LLMOutputError
from bumpless.llm.schemas import Rule
from bumpless.pipeline.context import RunContext
from bumpless.research.rulebook import norm_url

_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
_STOP = {
    "class", "def", "self", "cls", "True", "False", "None", "import", "from", "return", "int", "str", "bool",
    "float", "list", "dict", "for", "and", "not", "the", "with", "pass", "lambda", "value", "values", "Model",
    "BaseModel", "use", "new", "old", "foo", "bar", "obj", "data", "field", "fields", "kwargs", "args",
}
WINDOW = 2500
MAX_EXCERPT = 12_000


class Verdict(BaseModel):
    supported: bool
    quote: str = ""


def api_tokens(rule: Rule) -> list[str]:
    toks = _TOKEN.findall(f"{rule.old_pattern} {rule.new_pattern}")
    return list(dict.fromkeys(t for t in toks if t not in _STOP))


def mentioned(rule: Rule, text: str) -> list[str]:
    return [t for t in api_tokens(rule) if re.search(rf"\b{re.escape(t)}\b", text)]


def excerpt(text: str, tokens: list[str]) -> str:
    """Windows of page text around the API names, so huge pages stay cheap to check."""
    if len(text) <= MAX_EXCERPT:
        return text
    spans = []
    for t in tokens:
        for m in list(re.finditer(rf"\b{re.escape(t)}\b", text))[:2]:
            spans.append((max(0, m.start() - WINDOW), m.end() + WINDOW))
    spans.sort()
    merged: list[list[int]] = []
    for a, b in spans:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    out, used = [], 0
    for a, b in merged:
        if used >= MAX_EXCERPT:
            break
        out.append(text[a:b])
        used += b - a
    return "\n[...]\n".join(out)[:MAX_EXCERPT]


async def verify_rule(ctx: RunContext, rule: Rule, text: str) -> None:
    hits = mentioned(rule, text)
    if not hits:  # deterministic gate: the page never names the API, so it cannot support the rule
        rule.verified, rule.confidence = False, 0.0
        rule.notes = (rule.notes + " [unverified: source page does not mention the API]").strip()
        return
    try:
        v = await ctx.llm.chat("verify_rule", [{"role": "user", "content": prompts.render(
            "verify_rule", package=ctx.package, title=rule.title, old_pattern=rule.old_pattern,
            new_pattern=rule.new_pattern, url=rule.source_url, text=excerpt(text, hits))}],
            step="verify_sources", schema=Verdict, max_tokens=3000)
    except LLMOutputError:
        v = Verdict(supported=False)
    rule.verified = v.supported
    rule.confidence = (1.0 if rule.source_official else 0.7) if v.supported else 0.0
    if not v.supported:
        rule.notes = (rule.notes + " [unverified: source page does not support the rule]").strip()


async def verify_rules(ctx: RunContext, rules: list[Rule]) -> None:
    pages = ctx.sources.pages if ctx.sources else {}
    missing = [r.source_url for r in rules if norm_url(r.source_url) not in pages]
    if missing:
        for url, text in (await ctx.tavily.extract(missing)).items():
            pages[norm_url(url)] = text
    sem = asyncio.Semaphore(8)

    async def one(r: Rule) -> None:
        async with sem:
            await verify_rule(ctx, r, pages.get(norm_url(r.source_url), ""))

    await asyncio.gather(*[one(r) for r in rules])
    n = sum(r.verified for r in rules)
    ctx.progress("verify_sources", f"{n}/{len(rules)} rules verified against their source pages",
                 verified=n, total=len(rules))
