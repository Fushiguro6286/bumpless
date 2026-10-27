"""Bumpless CLI."""

import asyncio
import sys

import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from bumpless.llm.client import LLM, ModelConfigError, check_models
from bumpless.settings import settings

# Windows consoles default to cp1252, which cannot print ✓/✗.
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

app = typer.Typer(help="Dependabot bumps the version. Bumpless makes it pass.", no_args_is_help=True)
console = Console()


@app.callback()
def main() -> None:
    pass


@app.command()
def doctor() -> None:
    """Check configuration: models served on Token Factory, one tiny call per tier."""
    asyncio.run(_doctor())


async def _doctor() -> None:
    console.print(f"[bold]Token Factory[/] {settings.nebius_base_url}")
    try:
        await check_models()
    except ModelConfigError as e:
        console.print(f"[red]✗ {e}[/]")
        raise typer.Exit(1) from None
    console.print("[green]✓ all configured models are served[/]")

    llm = LLM(run_id="doctor", max_cost_usd=0.05)
    table = Table("tier", "model", "reply", "tokens in/out", "latency", "cost")
    ok = True
    for tier, model in settings.models.items():
        try:
            reply = await llm.chat("ping", [{"role": "user", "content": "Reply with exactly: OK"}],
                                   step="doctor", tier=tier, max_tokens=512)
            call = llm.calls[-1]
            table.add_row(tier, model, reply[:20] or "[yellow](empty)[/]",
                          f"{call['prompt_tokens']}/{call['completion_tokens']}",
                          f"{call['latency_s']:.2f}s", f"${call['cost_usd']:.6f}")
        except Exception as e:  # report every tier, don't stop at the first failure
            ok = False
            table.add_row(tier, model, f"[red]{type(e).__name__}: {str(e)[:80]}[/]", "-", "-", "-")
    console.print(table)
    console.print(f"Total doctor cost: [bold]${llm.spent:.6f}[/]")
    console.print(f"Tavily key: {'set' if settings.tavily_api_key else '[yellow]not set[/]'} · "
                  f"GitHub token: {'set' if settings.github_token else '[yellow]not set[/]'} · "
                  f"executor: {settings.executor}")
    if not ok:
        raise typer.Exit(1) from None


def _printer(event: dict) -> None:
    type, data = event["type"], event["data"]
    if type == "step_started":
        console.rule(f"[bold cyan]{data['step']}")
    elif type == "progress":
        console.print(f"  {escape(data['message'])}")
    elif type == "escalation":
        console.print(f"  [yellow]↑ {escape(data['message'])}[/]")
    elif type == "llm_call":
        console.print(f"  [dim]{data['tier']:<5} {data['task']:<10} "
                      f"{data['prompt_tokens']}→{data['completion_tokens']} tok "
                      f"{data['latency_s']:.1f}s ${data['cost_usd']:.5f} (run ${data['run_total_usd']:.4f})[/]")
    elif type == "tavily_call":
        console.print(f"  [dim]tavily {data['kind']} {'(cached) ' if data['cached'] else ''}"
                      f"{escape(data['query'][:90])} → {data['n_results']}[/]")
    elif type == "llm_retry":
        console.print(f"  [yellow]{escape(data['message'])}[/]")
    elif type == "step_finished":
        console.print(f"  [green]✓ {data['step']}[/] [dim]{data['duration_s']}s[/]")
    elif type == "error":
        console.print(f"[red]✗ {escape(data['message'])}[/]")


@app.command()
def run(
    repo: str = typer.Argument(..., help="GitHub URL or local path"),
    package: str = typer.Option(..., help="Package to upgrade, e.g. pydantic"),
    to: str = typer.Option(..., help='Target version spec, e.g. ">=2,<3"'),
    routing: str = typer.Option("tiered", help="tiered | all-ultra"),
    executor: str = typer.Option(None, help="docker | nebius | local (default: $EXECUTOR)"),
    open_pr: bool = typer.Option(False, "--open-pr", help="Push a branch and open a PR (needs GITHUB_TOKEN)"),
) -> None:
    """Migrate a repo to a new major version of a package."""
    from bumpless import events
    from bumpless.pipeline.run import run_migration

    asyncio.run(check_models())
    events.add_listener(_printer)
    result = asyncio.run(run_migration(repo, package, to, routing=routing, executor=executor, open_pr=open_pr))
    t = result["tests"]
    console.rule("[bold]result")
    colour = {"green": "green", "partial": "yellow"}.get(result["status"], "red")
    console.print(f"[bold {colour}]{result['status'].upper()}[/]  {result['package']} "
                  f"{result['old_version']} → {result['new_version']}  ({result['duration_s']}s)")
    for k, label in (("old", "old version"), ("new_before", "new version, before fix"), ("after", "after fix")):
        if k in t:
            console.print(f"  tests {label:<24} {t[k]['passed']} passed, {t[k]['failed']} failed")
    rb = result["rulebook"]
    if rb:
        console.print(f"  rulebook: {len(rb['rules'])} rules, {rb['official_pages']} official pages")
        verified = sum(r["verified"] for r in rb["rules"])
        console.print(f"  verified rules: {verified}/{len(rb['rules'])} (unverified rules are never applied)")
    ch = result.get("characterization") or {}
    if ch.get("observations"):
        after_char = [x for x in t.get("after", {}).get("failing", []) if x.startswith("tests._bumpless")]
        console.print(f"  characterization: {ch['observations']} behaviors recorded on old version; "
                      f"{ch['new_before']['failed']} differ before fix, {len(after_char)} differ after")
    rv = result.get("review") or {}
    if rv:
        console.print(f"  review: {'approved' if rv['approve'] else 'flagged'}; "
                      f"{len(rv['violations'])} guardrail violation(s)")
    cov = result.get("coverage") or {}
    if cov.get("measured"):
        pct = f"{cov['percent']}%" if cov["percent"] is not None else "n/a"
        console.print(f"  verified change coverage: [bold]{pct}[/] ({cov['executed_changed_lines']}/"
                      f"{cov['executable_changed_lines']} changed lines executed) · confidence {cov['by_confidence']}")
    if result.get("recipe_reused"):
        console.print("  [cyan]recipe reused: research skipped[/]")
    cost = result["cost"]
    tiers = "  ".join(f"{k} ${v:.4f}" for k, v in cost["by_tier"].items())
    console.print(f"  cost: [bold]${cost['total_usd']:.4f}[/]  ({tiers})  · {cost['llm_calls']} LLM calls, "
                  f"{result['tavily']['calls']} Tavily calls")
    if result["escalations"]:
        console.print(f"  escalations: {len(result['escalations'])}")
    for item in result["manual_review"]:
        console.print(f"  [yellow]needs review:[/] {escape(item)}")
    if result["error"]:
        console.print(f"  [red]{escape(result['error'])}[/]")
    console.print(f"  workspace: {result['workspace']}")
    o = result.get("output") or {}
    if o.get("pr_url"):
        console.print(f"  [bold green]PR:[/] {o['pr_url']}")
    elif o.get("report"):
        console.print(f"  report: {o['report']}")
        console.print(f"  patch:  {o['patch']}")
    if result["status"] == "failed":
        raise typer.Exit(1)


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the web app (API + built frontend)."""
    import uvicorn
    uvicorn.run("bumpless.api.app:app", host=host, port=port)


@app.command()
def bench(
    repos: str = typer.Argument("benchmarks/repos.yaml", help="Benchmark repo list"),
    routing: str = typer.Option("tiered", help="tiered | all-ultra"),
    executor: str = typer.Option(None, help="docker | nebius | local (default: $EXECUTOR)"),
    concurrency: int = typer.Option(2, help="Runs in parallel"),
    only: list[str] = typer.Option(None, help="Run only these repo names"),  # noqa: B008
) -> None:
    """Run the benchmark and store results in SQLite and benchmarks/results/."""
    from bumpless.bench import bench as run_bench

    asyncio.run(check_models())
    out = asyncio.run(run_bench(repos, routing=routing, executor=executor, concurrency=concurrency, only=only))
    table = Table("repo", "status", "tests fixed", "char. pass", "coverage", "time", "cost", "esc.", "recipe")
    for r in out["runs"]:
        rate = r["characterization_pass_rate"]
        table.add_row(r["name"], r["status"], f"{r['tests_fixed']}/{r['tests_failing_before_fix']}",
                      f"{rate:.0%}" if rate is not None else "-",
                      f"{r['coverage_percent']}%" if r["coverage_percent"] is not None else "-",
                      f"{r['duration_s']}s", f"${r['cost_usd']:.4f}", str(r["escalations"]),
                      "reused" if r["recipe_reused"] else "first run")
    console.print(table)
    s = out["summary"]
    console.print(f"[bold]{out['bench_id']}[/]: {s['green']} green / {s['partial']} partial / {s['failed']} failed · "
                  f"median coverage {s['median_coverage_percent']}% · median time {s['median_duration_s']}s · "
                  f"median cost ${s['median_cost_usd']} · total ${s['total_cost_usd']} · escalations {s['escalations']}")


recipes_app = typer.Typer(help="Migration recipes (verified rulebooks).")
app.add_typer(recipes_app, name="recipes")


@recipes_app.command("list")
def recipes_list() -> None:
    """List saved recipes with usage stats."""
    from bumpless.recipes import store

    table = Table("recipe", "version", "rules (verified)", "last checked", "runs", "success", "first run $", "reused $")
    for r in store.stats():
        def money(v):
            return f"{v:.4f}" if v is not None else "-"
        table.add_row(r["recipe"], str(r["recipe_version"]), f"{r['rules']} ({r['verified_rules']})",
                      r["checked_at"][:10], str(r["runs"]),
                      f"{r['success_rate']:.0%}" if r["success_rate"] is not None else "-",
                      money(r["avg_first_run_cost"]), money(r["avg_reused_run_cost"]))
    console.print(table)


if __name__ == "__main__":
    app()
