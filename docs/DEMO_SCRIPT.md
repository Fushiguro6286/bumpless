# Demo video script (≤ 3:00)

Record at 1080p. Live runs take 2–5 minutes, so record one beforehand and show it sped up (say "sped up"), or use
its replay at 4×. The replay page is labeled as a replay on screen. Every number you say must be on screen or in
`benchmarks/RESULTS.md` at recording time.

| Time | Screen | Say |
|---|---|---|
| 0:00–0:15 | A red Dependabot PR: `pydantic` 1.10 → 2.x, failing checks | "Dependabot bumps the version, CI goes red, and someone loses an afternoon to a migration guide. Bumpless finishes the job." |
| 0:15–0:30 | **Radar** page → `support_bot` fixture → Scan → backlog table (pydantic and openai behind a major, usage counts, risk, cost estimate) → click **Fix** on pydantic | "Radar shows the upgrade backlog: what's behind, how much code it touches, how risky it is, and what a fix costs, estimated from past runs." |
| 0:30–1:30 | **Live run view**: research step (Tavily calls, official pages, rules with ✓ verified) → characterize (behaviors recorded on the old version) → edit (parallel files, Nano badges, an escalation to Super/Ultra) → verify (red → green) → cost meter → verified change coverage | "Tavily finds the official migration guide, and every rule is checked against the page it came from. Before changing anything, it records how the code behaves today. Nano edits files in parallel, and a failed edit escalates to Super, then Ultra. Tests run in a sandbox: red to green. Verified change coverage shows which changed lines the tests actually ran." |
| 1:30–2:00 | GitHub: the PR gets a Bumpless commit and the report comment; a reviewer comments `@bumpless revert the change to app/storage.py`; Bumpless replies with tests and a commit. **If the Action hasn't run on GitHub yet:** the Result page's PR conversation panel (as Owner, then as Outside contributor to show it's ignored) | "It runs as a GitHub Action on Dependabot PRs. Reviewers talk to it. It revises, re-runs the tests and replies, and it ignores people without write access." |
| 2:00–2:40 | **Benchmark** page: success rate and the tiered vs all-Ultra cost chart, then the per-repo table; **Recipes** page (reuse count); README Results line on zero-shot SQLAlchemy | "We publish every benchmark run. Tiered routing is cheaper; all-Ultra has been more reliable so far, and it's one flag. Recipes let the next repo skip research. On SQLAlchemy, a package it had never seen, the first run went green, and we report the runs that didn't." |
| 2:40–3:00 | Logo + repo URL | "Dependabot bumps the version. Bumpless makes it pass." |

Checklist before recording:
- Fill the 1:30–2:00 segment with whichever version actually ran. Don't show the GitHub flow if it didn't run.
- Read the green/partial counts and costs from `benchmarks/RESULTS.md`; don't round in your favor.
