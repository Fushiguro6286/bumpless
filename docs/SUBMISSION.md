# Submission: Nebius x NVIDIA Global AI Hackathon

**Track:** Coding & Agentic Engineering · **Also entering:** Best Use of Tavily

| Field | Value |
|---|---|
| Project | Bumpless |
| Tagline | Dependabot bumps the version. Bumpless makes it pass. |
| Repository | https://github.com/Fushiguro6286/bumpless (MIT) · demo repo: https://github.com/Fushiguro6286/bumpless-demo |
| Live demo | https://bumpless.onrender.com (recorded real runs; first visit after idle takes about a minute) |
| Video (≤ 3 min) | 2:30 — upload `bumpless-demo.mp4` and paste the link here |

## Inspiration

Dependabot is great at noticing that `pydantic` 2 is out, and useless at what comes next. A major bump opens a
red PR, and then a person spends an afternoon reading a migration guide, grepping for old APIs, rewriting them
and hoping the tests cover it. Those PRs pile up. We wanted an agent that does that afternoon's work, and shows
enough evidence that a reviewer can trust it.

## What it does

Point Bumpless at a repo and a target version (or let the GitHub Action do it on a Dependabot PR).

1. **Tavily** finds the official migration guide and changelog. **Nemotron 3 Nano** turns each page into
   candidate rules and **Super** synthesizes a rulebook. Every rule is then checked against the page it came
   from, including whether the old usage really breaks, and only verified rules are applied.
2. It records how the code behaves on the old version as **characterization tests**.
3. **Ultra** plans. **Nano** edits files in parallel, and a failed edit escalates to Super, then Ultra.
   Guardrails reject edits that weaken tests.
4. Tests run in a Docker sandbox. **Ultra** diagnoses and repairs failures, looking up unknown errors with Tavily.
5. The report shows **verified change coverage** (which changed lines the tests ran) and a confidence, rule and
   source URL for every change.
6. Reviewers can reply `@bumpless revise / explain / revert` on the PR.
7. Verified rulebooks become **recipes** reused on the next repo. **Radar** shows a repo's upgrade backlog with risk
   and cost estimates.

## How we built it

- **Python + FastAPI + SQLite**, a Typer CLI, and a React/Vite/Tailwind UI with a live run view over SSE.
- **Nebius Token Factory** (OpenAI-compatible API) for every model call, with per-call cost accounting and caps.
- **NVIDIA Nemotron 3 Nano / Super / Ultra** with task-based routing and escalation, and an all-Ultra mode we
  benchmark against.
- **Tavily** search (raw markdown), extract and map, cached in SQLite, with source verification, recipe
  freshness and error lookup.
- **Nebius Serverless:** planned for hosting and for a Jobs sandbox executor, not done in time. We say so in the
  README.
- A benchmark harness that stores every run with its commit, plus replays of real runs for the demo.

## Challenges we ran into

- **Rules that are true but optional.** On SQLAlchemy, a rule like "use `where()` instead of `filter_by()`" was
  supported by the docs but only applies to the new query style. Applying it broke working code. Verification
  now also asks whether the old usage really breaks.
- **"Reply NONE if nothing applies"** turned out to be a strong attractor for Nemotron with reasoning off: 8 of
  9 tries said `NONE` on a guide page full of before/after code. A reworded prompt got 5 of 5.
- **Reasoning budgets.** With reasoning on, Nano/Super sometimes spent their whole 16k-token budget thinking
  about an edit. Edits now run with reasoning off, which halved tiered run time.
- **Honest benchmarks.** Results vary between runs of the same code, so we list every run and its commit
  instead of the best one.

## Accomplishments we're proud of

- pydantic v1 → v2 and openai 0.28 → 1.x migrations green on our fixtures, with every change cited to an
  official source and covered by tests (all-Ultra benchmark: 5/5 green, 37/37 broken tests fixed, $0.71 total).
- A real Dependabot PR fixed end to end by the GitHub Action: it detected the red major bump, migrated on the
  Actions runner, pushed the commit and commented the report (0 → 32 tests passing).
- Verified change coverage and characterization tests: evidence, not just a green check.
- A zero-shot SQLAlchemy 1.4 → 2.0 migration went green on its first try, and we published the runs that
  didn't.
- A PR conversation that refuses outside contributors before spending a single token.

## What we learned

- Grounding beats memory: Nano answering from memory invented pydantic changes, and fetched, verified sources
  fixed that.
- A cheap model is cheap only if its first attempt works. Most of our spend went to Ultra repairing failed
  edits, so better first edits are the biggest lever on cost.
- Small prompt wordings can flip results completely.

## What's next

- Real-world repos in the benchmark (pinned SHAs; the harness already supports them).
- The Nebius Serverless deployment and Jobs executor.
- More ecosystems after Python + pytest.
