"""Recipe reuse + freshness check: a stale recipe gets a Tavily search for changes since it was last checked."""

from datetime import UTC, datetime

from bumpless.llm.schemas import Rulebook
from bumpless.pipeline.context import RunContext
from bumpless.radar.pypi import official_sources, project_info
from bumpless.recipes import store
from bumpless.research import rulebook as research
from bumpless.research.verify_sources import verify_rules
from bumpless.settings import settings


async def official(ctx: RunContext) -> research.Sources:
    domains, repos = official_sources(await project_info(ctx.package))
    return research.Sources(domains, repos)


async def refresh(ctx: RunContext, recipe: Rulebook, usage: list[str]) -> int:
    """Look for breaking changes published since the recipe was checked; merge verified new rules."""
    since = recipe.checked_at[:10]
    src = ctx.sources
    hits = await ctx.tavily.search(
        f"{ctx.package} {recipe.to}.x release notes changelog breaking changes", search_depth="advanced",
        max_results=6, include_raw_content="markdown", start_date=since,
        include_domains=sorted(src.domains) + ["github.com"])
    for h in hits:
        src.add(h["url"], h.get("raw_content") or h.get("content") or "")
    added = 0
    if src.pages:
        notes = await research.summarize_pages(ctx, src, recipe.from_, recipe.to)
        if notes:
            new = await research.synthesize(ctx, src, notes, recipe.from_, recipe.to, usage, max_rules=5)
            await verify_rules(ctx, new)
            for r in new:
                r.learned_from_run = ctx.run_id
            added = len(store.merge(recipe, new))
    recipe.checked_at = datetime.now(UTC).isoformat(timespec="seconds")
    if added:
        recipe.recipe_version += 1
    return added


async def get_rulebook(ctx: RunContext, usage: list[str]) -> tuple[Rulebook, bool]:
    """(rulebook, reused). Reuses a saved recipe when one exists; otherwise researches from scratch."""
    recipe = store.load(ctx.package, ctx.from_major, ctx.to_major)
    if recipe is None:
        rb = await research.research(ctx, usage)
        await verify_rules(ctx, rb.rules)
        return rb, False
    ctx.sources = await official(ctx)
    ctx.emit("recipe_reused", step="research", recipe=f"{recipe.package}/{recipe.from_}-to-{recipe.to}",
             recipe_version=recipe.recipe_version, rules=len(recipe.rules), checked_at=recipe.checked_at)
    ctx.progress("research", f"Reusing recipe {recipe.package} {recipe.from_}→{recipe.to} "
                 f"v{recipe.recipe_version} ({len(recipe.rules)} rules); research skipped")
    if store.age_days(recipe) > settings.recipe_max_age_days:
        old_date = recipe.checked_at[:10] or "never"
        added = await refresh(ctx, recipe, usage)
        ctx.progress("research", f"Recipe was last checked {old_date}; checked for updates on "
                     f"{recipe.checked_at[:10]}: {added} new rule(s)", freshness_added=added)
    else:
        ctx.progress("research", f"Recipe checked for updates on {recipe.checked_at[:10]}")
    return recipe, True
