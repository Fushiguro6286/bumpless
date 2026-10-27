from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from bumpless.llm import router
from bumpless.llm.client import LLM, BudgetExceeded, LLMOutputError, cost_usd, parse_json, strip_reasoning


def test_router_tiered_and_escalation():
    assert router.tier_for("edit") == "nano"
    assert router.tier_for("edit", escalation=1) == "super"
    assert router.tier_for("edit", escalation=5) == "ultra"
    assert router.tier_for("plan") == "ultra"
    assert router.tier_for("rulebook") == "super"


def test_router_all_ultra():
    assert all(router.tier_for(t, "all-ultra") == "ultra" for t in router.TASK_TIERS)


def test_router_rejects_unknown():
    with pytest.raises(ValueError):
        router.tier_for("edit", "cheap")
    with pytest.raises(ValueError):
        router.tier_for("nope")


def test_cost():
    assert cost_usd("nano", 1_000_000, 1_000_000) == pytest.approx(0.30)
    assert cost_usd("ultra", 1000, 500) == pytest.approx(0.001 + 0.0015)


def test_strip_and_parse():
    assert strip_reasoning("<think>hmm {x}</think> hi") == "hi"
    assert strip_reasoning("reasoning...</think>\nOK") == "OK"
    assert parse_json('<think>{"no": 1}</think>Sure:\n```json\n{"a": [1, 2]}\n```') == {"a": [1, 2]}


class FakeClient:
    def __init__(self, replies, usage=(100, 50)):
        self.replies = list(replies)
        self.seen = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self.usage = usage

    async def _create(self, **kw):
        self.seen.append(kw)
        msg = SimpleNamespace(content=self.replies.pop(0))
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)],
                               usage=SimpleNamespace(prompt_tokens=self.usage[0], completion_tokens=self.usage[1]))


class Out(BaseModel):
    answer: int


async def test_chat_tracks_cost_and_routes():
    fake = FakeClient(["hello"])
    llm = LLM(run_id="t1", client=fake)
    assert await llm.chat("plan", [{"role": "user", "content": "x"}]) == "hello"
    assert fake.seen[0]["model"] == llm.cfg.models["ultra"]
    assert llm.spent == pytest.approx(cost_usd("ultra", 100, 50))
    assert llm.by_tier["ultra"] == llm.spent


async def test_chat_json_retry_then_ok():
    fake = FakeClient(["not json", '{"answer": "x"}', '{"answer": 42}'])
    out = await LLM(client=fake).chat("plan", [{"role": "user", "content": "x"}], schema=Out)
    assert out.answer == 42
    assert "invalid" in fake.seen[2]["messages"][-1]["content"]


async def test_chat_json_gives_up():
    fake = FakeClient(["no"] * 3)
    with pytest.raises(LLMOutputError):
        await LLM(client=fake).chat("plan", [], schema=Out)


async def test_budget_cap():
    fake = FakeClient(["a", "b"], usage=(1_000_000, 0))  # $1 per ultra call
    llm = LLM(client=fake, max_cost_usd=0.5)
    await llm.chat("plan", [])
    with pytest.raises(BudgetExceeded):
        await llm.chat("plan", [])


async def test_chat_json_last_retry_goes_one_tier_up():
    fake = FakeClient(["no", "still no", '{"answer": 1}'])
    llm = LLM(client=fake)
    assert (await llm.chat("rulebook", [], schema=Out)).answer == 1
    assert [c["tier"] for c in llm.calls] == ["super", "super", "ultra"]
