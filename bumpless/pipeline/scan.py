"""Step 4a: static scan with ast + rulebook detection regexes."""

import ast
import re
from collections import Counter
from pathlib import Path

from bumpless.llm.schemas import Rule

SKIP_DIRS = {".git", ".bumpless", ".venv", "venv", "node_modules", "__pycache__", "build", "dist", ".tox"}


def python_files(ws: Path) -> list[Path]:
    return sorted(p for p in ws.rglob("*.py") if not SKIP_DIRS & set(p.relative_to(ws).parts))


def _tree(path: Path) -> ast.AST | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return None


def imports_package(tree: ast.AST, package: str) -> bool:
    top = package.replace("-", "_").lower()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(a.name.split(".")[0].lower() == top for a in node.names):
            return True
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0].lower() == top:
            return True
    return False


def usage_identifiers(ws: Path, package: str) -> list[str]:
    """Names imported from the package plus attribute names used in files that import it (a research hint)."""
    names: Counter[str] = Counter()
    for f in python_files(ws):
        tree = _tree(f)
        if not tree or not imports_package(tree, package):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(package.replace("-", "_")):
                names.update(a.name for a in node.names)
            elif isinstance(node, ast.Attribute):
                names[node.attr] += 1
            elif isinstance(node, ast.ClassDef):
                names.update(n.name for n in node.body if isinstance(n, ast.ClassDef))  # e.g. Config
    return [n for n, _ in names.most_common(100)]


def compile_hint(rule: Rule) -> re.Pattern | None:
    if rule.detection_hint:
        try:
            return re.compile(rule.detection_hint, re.M)
        except re.error:
            pass
    m = re.search(r"[A-Za-z_]\w{2,}", rule.old_pattern)  # fall back to the first identifier
    return re.compile(rf"\b{re.escape(m.group())}\b") if m else None


def scan(ws: Path, rules: list[Rule], package: str) -> dict[str, dict]:
    """path -> {"imports": bool, "rules": {rule_id: [line numbers]}} for files that import or match."""
    hints = [(r.id, rx) for r in rules if (rx := compile_hint(r))]
    out = {}
    for f in python_files(ws):
        text = f.read_text(encoding="utf-8", errors="replace")
        tree = _tree(f)
        matches: dict[str, list[int]] = {}
        for rid, rx in hints:
            lines = sorted({text.count("\n", 0, m.start()) + 1 for m in rx.finditer(text)})
            if lines:
                matches[rid] = lines
        imports = bool(tree and imports_package(tree, package))
        if imports or matches:
            out[f.relative_to(ws).as_posix()] = {"imports": imports, "rules": matches}
    return out
