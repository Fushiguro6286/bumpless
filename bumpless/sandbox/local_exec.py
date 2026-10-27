"""Local subprocess executor with a throwaway venv.

Used inside GitHub Actions (the runner is the sandbox) and on the hosted demo for bundled
fixtures only. It cannot cut network access; never use it on untrusted code outside a sandbox.
"""

import asyncio
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

from bumpless.sandbox.base import ExecResult


class LocalExecutor:
    name = "local"

    def __init__(self, python: str = sys.executable):
        self.venv = Path(tempfile.mkdtemp(prefix="bumpless-venv-"))
        self.python = python
        self._ready = False

    def _env(self, extra: dict | None) -> dict:
        bindir = self.venv / ("Scripts" if os.name == "nt" else "bin")
        env = os.environ.copy() | {"VIRTUAL_ENV": str(self.venv), "PYTHONDONTWRITEBYTECODE": "1"}
        env["PATH"] = f"{bindir}{os.pathsep}{env.get('PATH', '')}"
        env.pop("PYTHONHOME", None)
        return env | (extra or {})

    async def run(self, workspace: Path, commands: list[str], env: dict | None = None,
                  timeout_s: int = 600, network: bool = False) -> ExecResult:
        t0 = time.perf_counter()
        if not self._ready:
            commands = [f'uv venv -q --python "{self.python}" "{self.venv}"', *commands]
            self._ready = True
        out = []
        for cmd in commands:
            proc = await asyncio.create_subprocess_shell(
                cmd, cwd=workspace, env=self._env(env),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            )
            try:
                data, _ = await asyncio.wait_for(proc.communicate(), timeout_s)
            except TimeoutError:
                proc.kill()
                return ExecResult(124, f"timed out after {timeout_s}s", time.perf_counter() - t0, True)
            out.append(data.decode("utf-8", "replace"))
            if proc.returncode != 0:
                return ExecResult(proc.returncode, "".join(out), time.perf_counter() - t0)
        return ExecResult(0, "".join(out), time.perf_counter() - t0)

    async def close(self) -> None:
        shutil.rmtree(self.venv, ignore_errors=True)
