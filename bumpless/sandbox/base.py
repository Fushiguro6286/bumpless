"""Executor interface: run shell commands against a workspace inside a sandbox with its own venv."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class ExecResult:
    exit_code: int
    output: str  # stdout + stderr
    duration_s: float
    timed_out: bool = False


class Executor(Protocol):
    name: str

    async def run(
        self, workspace: Path, commands: list[str], env: dict | None = None,
        timeout_s: int = 600, network: bool = False,
    ) -> ExecResult:
        """Run commands in order (stop at first failure). The sandbox venv is active.
        `network=False` must cut network access where the executor can (installs pass True)."""
        ...

    async def close(self) -> None: ...


def get_executor(name: str) -> Executor:
    if name == "docker":
        from bumpless.sandbox.docker_exec import DockerExecutor
        return DockerExecutor()
    if name == "local":
        from bumpless.sandbox.local_exec import LocalExecutor
        return LocalExecutor()
    if name == "nebius":
        from bumpless.sandbox.nebius_job_exec import NebiusJobExecutor
        return NebiusJobExecutor()
    raise ValueError(f"unknown executor {name!r} (docker|local|nebius)")
