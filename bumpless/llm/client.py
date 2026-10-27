"""Token Factory LLM client: one `chat()` that routes, tracks tokens/cost, enforces the budget,
and optionally parses + validates JSON output."""

import json
import re
import time
from functools import cache
from pathlib import Path

import yaml
from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from bumpless import events
from bumpless.llm import router
from bumpless.settings import ROOT, Settings, settings
from bumpless.storage import db


class BudgetExceeded(RuntimeError):
    pass


class LLMOutputError(RuntimeError):
    pass


class ModelConfigError(RuntimeError):
    pass


@cache
def pricing(path: Path = ROOT / "config" / "pricing.yaml") -> dict[str, dict[str, float]]:
    return yaml.safe_load(path.read_text())


def cost_usd(tier: str, prompt_tokens: int, completion_tokens: int) -> float:
    p = pricing()[tier]
    return (prompt_tokens * p["input"] + completion_tokens * p["output"]) / 1_000_000


_THINK = re.compile(r"<think>.*?</think>", re.S)


def strip_reasoning(text: str) -> str:
    text = _THINK.sub("", text or "")
    # Some templates emit only the closing tag (the opening one is in the prompt).
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1]
    return text.strip()


def parse_json(text: str):
    """First JSON object/array in the text (tolerates ``` fences and leading prose)."""
    text = strip_reasoning(text)
    starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
    if not starts:
        raise ValueError("no JSON object found in model output")
    obj, _ = json.JSONDecoder().raw_decode(text[min(starts):])
    return obj


class LLM:
    """One instance per run. Tracks spend against the run's budget cap."""

    def __init__(
        self,
        run_id: str | None = None,
        routing: str = "tiered",
        max_cost_usd: float | None = None,
        cfg: Settings = settings,
        client: AsyncOpenAI | None = None,
    ):
        if routing not in router.MODES:
            raise ValueError(f"unknown routing mode {routing!r}")
        self.run_id = run_id
        self.routing = routing
        self.cfg = cfg
        self.max_cost = cfg.max_run_cost_usd if max_cost_usd is None else max_cost_usd
        self.spent = 0.0
        self.by_tier: dict[str, float] = {"nano": 0.0, "super": 0.0, "ultra": 0.0}
        self.calls: list[dict] = []
        # The SDK retries 429/5xx/timeouts with exponential backoff.
        self.client = client or AsyncOpenAI(
            base_url=cfg.nebius_base_url, api_key=cfg.nebius_api_key or "missing", timeout=180, max_retries=4
        )

    async def chat(
        self,
        task: str,
        messages: list[dict],
        step: str = "",
        schema: type[BaseModel] | None = None,
        escalation: int = 0,
        tier: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ):
        """Returns the cleaned text, or a validated `schema` instance if `schema` is given."""
        tier = tier or router.tier_for(task, self.routing, escalation)
        msgs = list(messages)
        for attempt in range(3):  # first try + 2 retries on invalid JSON
            text = await self._call(task, step, tier, msgs, max_tokens, temperature)
            if schema is None:
                return text
            try:
                return schema.model_validate(parse_json(text))
            except (ValueError, ValidationError) as e:
                if attempt == 2:
                    raise LLMOutputError(f"{task}: model output failed validation after 3 tries: {e}") from e
                msgs = msgs + [
                    {"role": "assistant", "content": text[:4000]},
                    {"role": "user", "content": f"Your reply was invalid: {e}\nReply again with ONLY valid JSON."},
                ]
                if attempt == 1:  # last try on the next tier up: a stronger model usually fixes malformed JSON
                    tier = router.ESCALATION[min(router.ESCALATION.index(tier) + 1, len(router.ESCALATION) - 1)]

    async def _call(self, task, step, tier, messages, max_tokens, temperature) -> str:
        reasoning = task not in router.NO_REASONING_TASKS
        text, finish = await self._once(task, step, tier, messages, max_tokens, temperature, reasoning)
        if finish == "length" and reasoning:
            # Reasoning ran away and used the whole budget; one retry with reasoning off.
            events.emit(self.run_id, "llm_retry", {"step": step, "task": task, "tier": tier,
                                                   "message": f"{task} on {tier} hit max_tokens; retrying without reasoning"})
            text, _ = await self._once(task, step, tier, messages, max_tokens, temperature, False)
        return text

    async def _once(self, task, step, tier, messages, max_tokens, temperature, reasoning) -> tuple[str, str]:
        if self.spent >= self.max_cost:
            raise BudgetExceeded(
                f"Run budget of ${self.max_cost:.2f} reached (spent ${self.spent:.4f}). "
                "Raise MAX_RUN_COST_USD to continue."
            )
        model = self.cfg.models[tier]
        t0 = time.perf_counter()
        resp = await self.client.chat.completions.create(
            model=model, messages=messages, max_tokens=max_tokens, temperature=temperature,
            **({} if reasoning else {"extra_body": {"chat_template_kwargs": {"enable_thinking": False}}}),
        )
        latency = time.perf_counter() - t0
        pt = resp.usage.prompt_tokens if resp.usage else 0
        ct = resp.usage.completion_tokens if resp.usage else 0
        cost = cost_usd(tier, pt, ct)
        self.spent += cost
        self.by_tier[tier] += cost
        row = {
            "run_id": self.run_id, "ts": time.time(), "step": step, "task": task, "tier": tier,
            "model": model, "prompt_tokens": pt, "completion_tokens": ct,
            "latency_s": round(latency, 3), "cost_usd": cost,
        }
        self.calls.append(row)
        db.insert("llm_calls", row)
        events.emit(self.run_id, "llm_call", row | {"run_total_usd": self.spent})
        choice = resp.choices[0]
        return strip_reasoning(choice.message.content or ""), getattr(choice, "finish_reason", None) or "stop"


async def check_models(cfg: Settings = settings, client: AsyncOpenAI | None = None) -> dict[str, bool]:
    """GET /v1/models and confirm every configured model id is served. Raises with a clear message if not."""
    if not cfg.nebius_api_key:
        raise ModelConfigError("NEBIUS_API_KEY is not set. Copy .env.example to .env and add your Token Factory key.")
    client = client or AsyncOpenAI(base_url=cfg.nebius_base_url, api_key=cfg.nebius_api_key, timeout=30)
    served = {m.id async for m in client.models.list()}
    status = {tier: model in served for tier, model in cfg.models.items()}
    missing = [f"MODEL_{t.upper()}={cfg.models[t]}" for t, ok in status.items() if not ok]
    if missing:
        nemotron = sorted(m for m in served if "nemotron" in m.lower())
        raise ModelConfigError(
            f"These configured models are not served by {cfg.nebius_base_url}: " + ", ".join(missing)
            + "\nServed Nemotron models: " + (", ".join(nemotron) or "(none)")
        )
    return status
