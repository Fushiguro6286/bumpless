"""Model routing policy: which Nemotron tier handles which task.

Nano for cheap high-volume calls, Super for long-context structured work,
Ultra for serious reasoning. `all-ultra` mode exists for the cost benchmark.
"""

TASK_TIERS: dict[str, str] = {
    "summarize": "nano",        # clean individual Tavily results
    "verify_rule": "nano",      # does this page support this rule? many yes/no calls
    "rulebook": "super",        # synthesize rulebook from many docs (long context)
    "probe": "super",           # design characterization probes
    "comment_intent": "super",  # classify @bumpless comment
    "radar_risk": "super",      # per-dependency risk estimate
    "plan": "ultra",            # migration plan
    "edit": "nano",             # per-file edits (escalates on failure)
    "diagnose": "ultra",        # test-failure diagnosis / repair
    "revision_plan": "ultra",   # plan a revision requested in a PR comment
    "review": "ultra",          # final review + guardrail check
    "ping": "nano",             # doctor health check (tier given explicitly)
}

ESCALATION = ["nano", "super", "ultra"]
# Simple extraction / yes-no tasks run with Nemotron's reasoning turned off: same answers, a fraction of the tokens.
NO_REASONING_TASKS = {"summarize", "verify_rule", "ping"}
MODES = ("tiered", "all-ultra")


def tier_for(task: str, mode: str = "tiered", escalation: int = 0) -> str:
    """Tier for a task. `escalation` steps up the ladder (used after repeated edit failures)."""
    if mode not in MODES:
        raise ValueError(f"unknown routing mode {mode!r}; use one of {MODES}")
    if task not in TASK_TIERS:
        raise ValueError(f"unknown task {task!r}")
    if mode == "all-ultra":
        return "ultra"
    base = ESCALATION.index(TASK_TIERS[task])
    return ESCALATION[min(base + escalation, len(ESCALATION) - 1)]
