"""Step 4a: static scan with ast + rulebook detection regexes."""

import ast
import re
from collections import Counter
from pathlib import Path

from bumpless.llm.schemas import Rule

SKIP_DIRS = {".git", ".bumpless", ".venv", "venv", "node_modules", "__pycache__", "build", "dist", ".tox"}


GENERATED = "tests/_bumpless/"  # Bumpless's own characterization files: never scanned or edited


def python_files(ws: Path) -> list[Path]:
    return sorted(p for p in ws.rglob("*.py") if not SKIP_DIRS & set(p.relative_to(ws).parts)
                  and not p.relative_to(ws).as_posix().startswith(GENERATED))


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


def module_name(ws: Path, f: Path) -> str:
    parts = list(f.relative_to(ws).with_suffix("").parts)
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def imported_modules(tree: ast.AST) -> set[str]:
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
            out.update(f"{node.module}.{a.name}" for a in node.names)
    return out


def scan(ws: Path, rules: list[Rule], package: str) -> dict[str, dict]:
    """path -> {"imports": bool, "uses": bool, "rules": {rule_id: [lines]}} for files that import the package,
    import a module that does (one hop, e.g. code calling .dict() on models defined elsewhere), or match a rule."""
    hints = [(r.id, rx) for r in rules if (rx := compile_hint(r))]
    files = python_files(ws)
    trees = {f: _tree(f) for f in files}
    direct = {module_name(ws, f) for f, t in trees.items() if t and imports_package(t, package)}
    out = {}
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        tree = trees[f]
        matches: dict[str, list[int]] = {}
        for rid, rx in hints:
            lines = sorted({text.count("\n", 0, m.start()) + 1 for m in rx.finditer(text)})
            if lines:
                matches[rid] = lines
        imports = bool(tree and imports_package(tree, package))
        uses = bool(tree) and not imports and bool(imported_modules(tree) & direct)
        if imports or uses or matches:
            out[f.relative_to(ws).as_posix()] = {"imports": imports, "uses": uses, "rules": matches}
    return out
