"""Docker sandbox: non-root, CPU/memory limits, network only for installs, hard timeout."""

import asyncio
import time
import uuid
from pathlib import Path

from bumpless.sandbox.base import ExecResult
from bumpless.settings import ROOT

IMAGE = "bumpless-sandbox:1"


async def _sh(*args: str, timeout: float | None = None) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    out, _ = await asyncio.wait_for(proc.communicate(), timeout)
    return proc.returncode, out.decode("utf-8", "replace")


class DockerExecutor:
    name = "docker"

    def __init__(self, cpus: str = "2", memory: str = "2g"):
        self.volume = f"bumpless-venv-{uuid.uuid4().hex[:10]}"
        self.cpus, self.memory = cpus, memory
        self._ready = False

    async def _ensure_image(self) -> None:
        if self._ready:
            return
        code, _ = await _sh("docker", "image", "inspect", IMAGE)
        if code != 0:
            code, out = await _sh("docker", "build", "-q", "-t", IMAGE, str(ROOT / "sandbox"), timeout=900)
            if code != 0:
                raise RuntimeError(f"could not build sandbox image:\n{out[-2000:]}")
        self._ready = True

    async def run(self, workspace: Path, commands: list[str], env: dict | None = None,
                  timeout_s: int = 600, network: bool = False) -> ExecResult:
        await self._ensure_image()
        name = f"bumpless-{uuid.uuid4().hex[:10]}"
        args = ["docker", "run", "--rm", "--name", name, "--cpus", self.cpus, "--memory", self.memory,
                "--mount", f"type=bind,source={workspace.resolve()},target=/work",
                "--mount", f"type=volume,source={self.volume},target=/venv",
                "--mount", "type=volume,source=bumpless-uvcache,target=/uvcache"]
        if not network:
            args += ["--network", "none"]
        for k, v in (env or {}).items():
            args += ["-e", f"{k}={v}"]
        script = "set -e\n[ -x /venv/bin/python ] || uv venv -q /venv\n" + "\n".join(commands)
        args += [IMAGE, "sh", "-c", script]
        t0 = time.perf_counter()
        try:
            code, out = await _sh(*args, timeout=timeout_s)
            return ExecResult(code, out, time.perf_counter() - t0)
        except TimeoutError:
            await _sh("docker", "kill", name)
            return ExecResult(124, f"timed out after {timeout_s}s", time.perf_counter() - t0, timed_out=True)

    async def close(self) -> None:
        await _sh("docker", "volume", "rm", "-f", self.volume)
