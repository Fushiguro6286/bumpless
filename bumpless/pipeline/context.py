"""Shared state for one run."""

from dataclasses import dataclass, field
from pathlib import Path

from bumpless import events
from bumpless.llm.client import LLM
from bumpless.llm.schemas import Plan, Rulebook
from bumpless.research.tavily_client import Tavily
from bumpless.sandbox.base import Executor


@dataclass
class PinRef:
    file: str
    line_no: int  # 0-based
    text: str


@dataclass
class TestRun:
    passed: int = 0
    repo_passed: int = 0  # passes outside the generated characterization tests
    failed: int = 0  # failures + errors
    skipped: int = 0
    failing: list[str] = field(default_factory=list)
    output: str = ""

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.skipped

    def summary(self) -> dict:
        return {"passed": self.passed, "repo_passed": self.repo_passed, "failed": self.failed, "skipped": self.skipped,
                "total": self.total, "failing": self.failing}


@dataclass
class Hunk:
    """One applied edit block, with provenance for citations and confidence."""
    path: str
    rule_id: str
    search: str
    replace: str
    model_tier: str
    escalated: bool = False
    repaired: bool = False
    iteration: int = 0  # repair iteration that produced it (0 = initial edit)


@dataclass
class RunContext:
    run_id: str
    workspace: Path
    package: str
    target: str  # version spec, e.g. ">=2,<3"
    llm: LLM
    tavily: Tavily
    executor: Executor
    test_cmd: str = "python -m pytest -q"
    pins: list[PinRef] = field(default_factory=list)
    install_cmds: list[str] = field(default_factory=list)
    old_version: str = ""
    new_version: str = ""
    tests: dict[str, TestRun] = field(default_factory=dict)  # old / new_before / after
    rulebook: Rulebook | None = None
    sources: object = None  # research.rulebook.Sources (fetched pages), reused for verification + repair
    scan: dict = field(default_factory=dict)
    plan: Plan | None = None
    hunks: list[Hunk] = field(default_factory=list)
    characterization: dict = field(default_factory=dict)
    review: dict = field(default_factory=dict)
    coverage: dict = field(default_factory=dict)
    recipe_reused: bool = False
    repo_names: set = field(default_factory=set)  # functions/classes the repo defines
    manual_review: list[str] = field(default_factory=list)
    escalations: list[dict] = field(default_factory=list)
    status: str = "running"

    @property
    def from_major(self) -> str:
        return self.old_version.split(".")[0]

    @property
    def to_major(self) -> str:
        return self.new_version.split(".")[0]

    def emit(self, type: str, **data) -> None:
        events.emit(self.run_id, type, data)

    def progress(self, step: str, message: str, **data) -> None:
        self.emit("progress", step=step, message=message, **data)
