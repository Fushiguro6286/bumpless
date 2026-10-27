"""Step 0: copy/clone the repo into a workspace, find version pins and the install command."""

import re
import shutil
import tempfile
from pathlib import Path

import git

from bumpless import fsutil
from bumpless.pipeline.context import PinRef

IGNORE = shutil.ignore_patterns(".git", ".venv", "venv", "__pycache__", "node_modules", ".bumpless",
                                ".pytest_cache", ".mypy_cache", ".ruff_cache", "*.pyc")
DEP_FILES = ("requirements*.txt", "pyproject.toml", "setup.py", "setup.cfg")
ACTOR = git.Actor("Bumpless", "bumpless@users.noreply.github.com")
_SPEC = r"[<>=!~][^\"';#\s,]*"


def pin_regex(package: str) -> re.Pattern:
    name = r"[-_.]+".join(map(re.escape, re.split(r"[-_.]+", package)))
    # package name, optional [extras], optional version spec; must end at a quote, comment, comma or EOL
    return re.compile(
        rf"(?<![\w.-])(?P<name>{name})(?P<extras>\[[^\]]*\])?"
        rf"(?P<spec>\s*{_SPEC}(?:\s*,\s*{_SPEC})*)?(?=\s*[\"';#,]|\s*$)",
        re.I,
    )


def find_pins(ws: Path, package: str) -> list[PinRef]:
    rx = pin_regex(package)
    pins = []
    for pattern in DEP_FILES:
        for f in sorted(ws.glob(pattern)):
            for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines()):
                if line.lstrip().startswith("#"):
                    continue
                m = rx.search(line)
                # requirements.txt / setup.cfg: bare lines. pyproject.toml / setup.py: inside a quoted string.
                if m and (f.suffix in (".txt", ".cfg") or line[m.start() - 1:m.start()] in ("'", '"')):
                    pins.append(PinRef(f.relative_to(ws).as_posix(), i, line))
    return pins


def bump_line(line: str, package: str, target: str) -> str:
    return pin_regex(package).sub(lambda m: f"{m.group('name')}{m.group('extras') or ''}{target}", line, count=1)


def apply_pin_bumps(ws: Path, pins: list[PinRef], package: str, target: str) -> list[dict]:
    """Rewrite each pin line to the target spec. Deterministic: no LLM involved."""
    changes = []
    for pin in pins:
        f = ws / pin.file
        lines = fsutil.read(f).split("\n")
        new = bump_line(lines[pin.line_no], package, target)
        if new != lines[pin.line_no]:
            changes.append({"file": pin.file, "old": lines[pin.line_no], "new": new})
            lines[pin.line_no] = new
            fsutil.write(f, "\n".join(lines))
    return changes


def install_commands(ws: Path) -> list[str]:
    reqs = sorted(p.name for p in ws.glob("requirements*.txt"))
    cmds = []
    if reqs:
        cmds.append("uv pip install -q " + " ".join(f"-r {r}" for r in reqs))
    elif (ws / "pyproject.toml").exists() or (ws / "setup.py").exists():
        cmds.append("uv pip install -q -e .")
    cmds.append("uv pip install -q pytest coverage")
    return cmds


def prepare_workspace(source: str, run_id: str, ref: str | None = None) -> Path:
    """`ref`: a commit SHA to pin a remote repo to (benchmarks)."""
    root = Path(tempfile.mkdtemp(prefix=f"bumpless-{run_id}-"))
    ws = root / "repo"
    if re.match(r"^(https?://|git@)", source) and ref:
        repo = git.Repo.init(ws)
        repo.create_remote("origin", source)
        repo.git.fetch("--depth", "1", "origin", ref)
        repo.git.checkout("FETCH_HEAD")
    elif re.match(r"^(https?://|git@)", source):
        git.Repo.clone_from(source, ws, depth=1)
    else:
        shutil.copytree(Path(source), ws, ignore=IGNORE)
        repo = git.Repo.init(ws)
        repo.git.add(A=True)
        repo.index.commit("baseline", author=ACTOR, committer=ACTOR)
    (ws / ".bumpless").mkdir(exist_ok=True)
    with open(ws / ".git" / "info" / "exclude", "a") as f:
        f.write("\n.bumpless/\n__pycache__/\n*.pyc\n.coverage\n")
    return ws
