"""Step 1: tests on the old version, then on the new version before any fix (the "Dependabot red")."""

import xml.etree.ElementTree as ET

from bumpless.pipeline.context import RunContext, TestRun

JUNIT = ".bumpless/junit.xml"


async def installed_version(ctx: RunContext) -> str:
    r = await ctx.executor.run(ctx.workspace, [
        f"python -c \"import importlib.metadata as m; print(m.version('{ctx.package}'))\""])
    if r.exit_code != 0:
        raise RuntimeError(f"{ctx.package} is not installed in the sandbox:\n{r.output[-1000:]}")
    return r.output.strip().splitlines()[-1]


async def install(ctx: RunContext, extra: list[str] | None = None) -> None:
    r = await ctx.executor.run(ctx.workspace, ctx.install_cmds + (extra or []), network=True, timeout_s=900)
    if r.exit_code != 0:
        raise RuntimeError(f"dependency install failed:\n{r.output[-2000:]}")


def parse_junit(path, output: str) -> TestRun:
    run = TestRun(output=output)
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        run.failed, run.failing = 1, ["<pytest did not produce a report>"]
        return run
    for case in root.iter("testcase"):
        cid = f"{case.get('classname', '')}::{case.get('name', '')}"
        if case.find("failure") is not None or case.find("error") is not None:
            run.failed += 1
            run.failing.append(cid)
        elif case.find("skipped") is not None:
            run.skipped += 1
        else:
            run.passed += 1
    return run


async def run_tests(ctx: RunContext, extra_args: str = "") -> TestRun:
    junit = ctx.workspace / JUNIT
    junit.unlink(missing_ok=True)
    cmd = f"{ctx.test_cmd} -p no:cacheprovider --junitxml={JUNIT} {extra_args}".strip()
    r = await ctx.executor.run(ctx.workspace, [cmd], timeout_s=900)
    return parse_junit(junit, r.output)


async def baseline(ctx: RunContext) -> None:
    await install(ctx)
    ctx.old_version = await installed_version(ctx)
    ctx.tests["old"] = old = await run_tests(ctx)
    ctx.progress("baseline", f"{ctx.package} {ctx.old_version}: {old.passed} passed, {old.failed} failed",
                 tests=old.summary())
    await install(ctx, [f'uv pip install -q "{ctx.package}{ctx.target}"'])
    ctx.new_version = await installed_version(ctx)
    ctx.tests["new_before"] = red = await run_tests(ctx)
    ctx.progress("baseline", f"{ctx.package} {ctx.new_version} before fix: {red.passed} passed, "
                 f"{red.failed} failed", tests=red.summary())
