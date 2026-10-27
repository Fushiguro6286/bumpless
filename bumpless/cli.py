"""Bumpless CLI."""

import asyncio
import sys

import typer
from rich.console import Console
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


def _printer(run_id, type, data) -> None:
    if type == "step_started":
        console.rule(f"[bold cyan]{data['step']}")
    elif type == "progress":
        console.print(f"  {data['message']}")
    elif type == "escalation":
        console.print(f"  [yellow]↑ {data['message']}[/]")
    elif type == "llm_call":
        console.print(f"  [dim]{data['tier']:<5} {data['task']:<10} "
                      f"{data['prompt_tokens']}→{data['completion_tokens']} tok "
                      f"{data['latency_s']:.1f}s ${data['cost_usd']:.5f} (run ${data['run_total_usd']:.4f})[/]")
    elif type == "tavily_call":
        console.print(f"  [dim]tavily {data['kind']} {'(cached) ' if data['cached'] else ''}"
                      f"{data['query'][:90]} → {data['n_results']}[/]")
    elif type == "step_finished":
        console.print(f"  [green]✓ {data['step']}[/] [dim]{data['duration_s']}s[/]")
    elif type == "error":
        console.print(f"[red]✗ {data['message']}[/]")


@app.command()
def run(
    repo: str = typer.Argument(..., help="GitHub URL or local path"),
    package: str = typer.Option(..., help="Package to upgrade, e.g. pydantic"),
    to: str = typer.Option(..., help='Target version spec, e.g. ">=2,<3"'),
    routing: str = typer.Option("tiered", help="tiered | all-ultra"),
    executor: str = typer.Option(None, help="docker | nebius | local (default: $EXECUTOR)"),
) -> None:
    """Migrate a repo to a new major version of a package."""
    from bumpless import events
    from bumpless.pipeline.run import run_migration

    asyncio.run(check_models())
    events.add_listener(_printer)
    result = asyncio.run(run_migration(repo, package, to, routing=routing, executor=executor))
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
    cost = result["cost"]
    tiers = "  ".join(f"{k} ${v:.4f}" for k, v in cost["by_tier"].items())
    console.print(f"  cost: [bold]${cost['total_usd']:.4f}[/]  ({tiers})  · {cost['llm_calls']} LLM calls, "
                  f"{result['tavily']['calls']} Tavily calls")
    if result["escalations"]:
        console.print(f"  escalations: {len(result['escalations'])}")
    for item in result["manual_review"]:
        console.print(f"  [yellow]needs review:[/] {item}")
    if result["error"]:
        console.print(f"  [red]{result['error']}[/]")
    console.print(f"  workspace: {result['workspace']}")
    if result["status"] == "failed":
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
