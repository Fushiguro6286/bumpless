from types import SimpleNamespace

from bumpless.llm.schemas import Rule
from bumpless.pipeline.context import Hunk
from bumpless.pipeline.coverage import change_coverage, confidence, parse_diff

DIFF = """diff --git a/app/m.py b/app/m.py
index 1..2 100644
--- a/app/m.py
+++ b/app/m.py
@@ -3 +3 @@ x
-    return u.dict()
+    return u.model_dump()
@@ -10,2 +10,3 @@ y
-def save(u):
-    return u.json()
+
+def save(u):
+    return u.model_dump_json()
diff --git a/requirements.txt b/requirements.txt
--- a/requirements.txt
+++ b/requirements.txt
@@ -1 +1 @@
-pydantic==1
+pydantic>=2,<3
"""

# line 3 executed; lines 11-12 executable but never run; line 10 blank (not executable)
COV = {"files": {"app/m.py": {"executed_lines": [1, 2, 3], "missing_lines": [11, 12]}}}


def test_parse_diff_line_numbers():
    hunks = parse_diff(DIFF)
    assert [(h.path, list(h.added)) for h in hunks] == [
        ("app/m.py", [3]), ("app/m.py", [10, 11, 12]), ("requirements.txt", [1])]
    assert hunks[0].removed == ["    return u.dict()"]


def test_change_coverage_matches_manual_count():
    hunks = [h for h in parse_diff(DIFF) if h.path.endswith(".py")]
    hit, total, _ = change_coverage(hunks, COV)
    # manual: executable changed lines are 3, 11, 12; only 3 ran
    assert (hit, total) == (1, 3)


def _ctx(hunks):
    rules = [Rule(id="R001", title="t", old_pattern=".dict()", new_pattern=".model_dump()", source_url="u",
                  source_official=True, verified=True),
             Rule(id="R002", title="t", old_pattern=".json()", new_pattern=".model_dump_json()", source_url="u",
                  source_official=True, verified=True)]
    return SimpleNamespace(rulebook=SimpleNamespace(rules=rules), hunks=hunks)


def test_confidence_levels():
    h_tested, h_untested = [h for h in parse_diff(DIFF) if h.path.endswith(".py")]
    edits = [Hunk("app/m.py", "R001", "u.dict()", "    return u.model_dump()", "nano"),
             Hunk("app/m.py", "R002", "u.json()", "    return u.model_dump_json()", "nano")]
    exe, ran = {1, 2, 3, 11, 12}, {1, 2, 3}
    assert confidence(_ctx(edits), h_tested, ran, exe)[0] == "High"
    level, why = confidence(_ctx(edits), h_untested, ran, exe)
    assert level == "Low" and "not executed" in why[0]
    edits[0].escalated = True
    assert confidence(_ctx(edits), h_tested, ran, exe)[0] == "Medium"
    unverified = _ctx([Hunk("app/m.py", "R009", "", "    return u.model_dump()", "nano")])
    assert confidence(unverified, h_tested, ran, exe)[0] == "Low"
