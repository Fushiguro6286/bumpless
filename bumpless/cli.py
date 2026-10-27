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


if __name__ == "__main__":
    app()
