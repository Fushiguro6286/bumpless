"""Check a candidate benchmark repo before adding it to repos.yaml: tests must pass on the old version.

    uv run python benchmarks/check_baseline.py <git url> <sha> <package> "<target spec>"

Runs in the Docker sandbox (repo code never runs on the host). No LLM or Tavily calls.
"""

import asyncio
import sys
import uuid

from bumpless.pipeline import baseline, intake
from bumpless.pipeline.context import RunContext
from bumpless.sandbox.base import get_executor


async def check(url: str, sha: str, package: str, target: str) -> None:
    run_id = "check-" + uuid.uuid4().hex[:6]
    ex = get_executor("docker")
    ctx = RunContext(run_id=run_id, workspace=intake.prepare_workspace(url, run_id, sha), package=package,
                     target=target, llm=None, tavily=None, executor=ex)
    try:
        ctx.pins = intake.find_pins(ctx.workspace, package)
        ctx.install_cmds = intake.install_commands(ctx.workspace)
        print("pins:", [f"{p.file}: {p.text.strip()}" for p in ctx.pins])
        print("install:", ctx.install_cmds)
        await baseline.baseline(ctx)
    except Exception as e:  # report and move on to the next candidate
        print(f"FAILED: {type(e).__name__}: {str(e)[-1500:]}")
        return
    finally:
        await ex.close()
    for k, t in ctx.tests.items():
        print(f"{k}: {t.passed} passed, {t.failed} failed, {t.skipped} skipped")
    old = ctx.tests["old"]
    ok = old.passed > 0 and old.failed == 0
    print(f"{ctx.package} {ctx.old_version} -> {ctx.new_version}: {'OK to add' if ok else 'NOT usable'}")
    if not ok:
        print(old.output[-2500:])


if __name__ == "__main__":
    asyncio.run(check(*sys.argv[1:5]))
