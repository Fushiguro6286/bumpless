# Demo video script (≤ 3:00)

Record at 1080p. The live run happens beforehand; in the video, use the replay at 4× (labeled as a replay on
screen) or speed up the recording, and say so. Numbers spoken must match the run shown.

| Time | Screen | Say |
|---|---|---|
| 0:00–0:15 | A Dependabot PR: pydantic 1.10 → 2.x, CI red | "Dependabot bumps the version. Then a human spends an afternoon reading a migration guide. Bumpless finishes the job." |
| 0:15–0:35 | New migration page → pick `pydantic_app` → Run | "Point it at a repo and a target version. Everything runs on NVIDIA Nemotron through Nebius Token Factory, with Tavily for research." |
| 0:35–1:05 | Live run: research step, Tavily calls, rule list with ✓ verified | "Tavily finds the official migration guide. Nano reads every page and proposes rules, and each rule is checked against the page it came from. Unverified rules are never applied." |
| 1:05–1:25 | Characterize step | "Before changing anything, it records how the code behaves on the old version and turns that into tests. The migration has to keep that behavior." |
| 1:25–1:50 | Edit + verify: model-call list with Nano / Super / Ultra badges, an escalation | "Ultra plans, Nano edits file by file, and a failed edit escalates. Tests run in a Docker sandbox; failures go to Ultra for diagnosis and repair." |
| 1:50–2:15 | Result: tests red → green, verified change coverage, a Low-confidence row | "All tests green. Verified change coverage shows which changed lines the tests actually ran. This file isn't tested, so it's marked Low confidence for a human to review. Cost: [read from screen]." |
| 2:15–2:35 | PR conversation panel: `@bumpless revert the change to app/storage.py` (Owner), then the same as an outside contributor | "Reviewers talk to it on the PR. It reverts, re-runs the tests and replies. A comment from someone without write access is ignored before any model call." |
| 2:35–2:50 | Benchmark page: tiered vs all-Ultra; Recipes page | "We benchmark both routings on the same repos and publish every run. Tiered is cheaper, all-Ultra is more reliable so far, and the switch is one flag. A saved recipe lets the next repo skip research." (Say only numbers that are in RESULTS.md at recording time.) |
| 2:50–3:00 | README / repo URL | "Bumpless: open source, MIT. Link below." |

Before recording, check every spoken number against `benchmarks/RESULTS.md` and the screen.
