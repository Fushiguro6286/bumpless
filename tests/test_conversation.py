import git

from bumpless import conversation
from bumpless.pipeline.context import RunContext
from bumpless.sandbox.base import ExecResult

JUNIT = '<testsuite><testcase classname="tests.test_a" name="t1"/></testsuite>'


class FakeLLM:
    routing, spent = "tiered", 0.0

    def __init__(self, replies):
        self.replies, self.calls = list(replies), 0

    async def chat(self, task, messages, step="", schema=None, **kw):
        self.calls += 1
        r = self.replies.pop(0)
        return schema.model_validate(r) if schema else r


class FakeExecutor:
    name = "fake"

    async def run(self, ws, commands, **kw):
        if any("--junitxml" in c and "coverage" not in c for c in commands):
            (ws / ".bumpless" / "junit.xml").write_text(JUNIT)
        return ExecResult(exit_code=0 if not any("coverage json" in c for c in commands) else 1, output="",
                          duration_s=0.0)

    async def close(self):
        pass


def repo_with_migration(tmp_path):
    ws = tmp_path / "repo"
    ws.mkdir()
    (ws / ".bumpless").mkdir()
    (ws / "a.py").write_text("x = old()\n")
    (ws / "b.py").write_text("y = old()\n")
    r = git.Repo.init(ws)
    r.git.add("a.py", "b.py")
    r.index.commit("baseline")
    base = r.head.commit.hexsha
    (ws / "a.py").write_text("x = new()\n")
    (ws / "b.py").write_text("y = new()\n")
    r.git.add("a.py", "b.py")
    r.index.commit("migration")
    return ws, base


def ctx_for(ws, llm):
    return RunContext(run_id="t", workspace=ws, package="pkg", target="", llm=llm, tavily=None,
                      executor=FakeExecutor())


async def test_non_collaborators_and_non_trigger_are_ignored_without_model_calls(tmp_path):
    ws, base = repo_with_migration(tmp_path)
    llm = FakeLLM([])
    out = await conversation.handle(ctx_for(ws, llm), "@bumpless revert a.py", "CONTRIBUTOR", base)
    assert out["acted"] is False and out["reply"] == conversation.NOT_ALLOWED
    out = await conversation.handle(ctx_for(ws, llm), "looks good to me", "OWNER", base)
    assert out == {"acted": False, "intent": None, "reply": None}
    assert llm.calls == 0


async def test_revert_only_touches_the_named_file_and_commits(tmp_path):
    ws, base = repo_with_migration(tmp_path)
    (ws / ".git" / "info" / "exclude").write_text(".bumpless/\n")  # as in a real workspace (regression)
    llm = FakeLLM([{"intent": "revert", "files": ["a.py", "../etc/passwd"], "instruction": "revert a.py"}])
    out = await conversation.handle(ctx_for(ws, llm), "@bumpless revert the change to a.py", "COLLABORATOR", base)
    assert out["intent"] == "revert" and out["files"] == ["a.py"] and out["commit"]
    assert (ws / "a.py").read_text() == "x = old()\n" and (ws / "b.py").read_text() == "y = new()\n"
    assert "1 passed, 0 failed" in out["reply"]
    head = git.Repo(ws).head.commit
    assert head.message.startswith("Revert Bumpless changes to a.py")
    assert list(head.stats.files) == ["a.py"]  # no .bumpless/ scratch files committed
