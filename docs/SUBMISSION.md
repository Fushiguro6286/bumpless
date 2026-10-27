# Submission: Nebius x NVIDIA Global AI Hackathon

**Track:** Coding & Agentic Engineering · **Also entering:** Best Use of Tavily

| Field | Value |
|---|---|
| Project | Bumpless |
| One-liner | Dependabot bumps the version. Bumpless makes it pass. |
| Repository | TODO (public, MIT) |
| Live demo | TODO (replays work without keys; live runs are budget-capped) |
| Video (≤ 3 min) | TODO |

## What it does (short)

Bumpless is an agent that finishes major-version dependency upgrades that Dependabot opens and CI fails. It
researches the official migration guide with Tavily and turns it into a rulebook whose rules are each checked
against their source. It records the code's current behavior as characterization tests, then migrates the code
with NVIDIA Nemotron 3 (Nano edits, Super escalates, Ultra plans, diagnoses and reviews) on Nebius Token Factory.
It proves the result with tests in a sandbox and **verified change coverage**, and opens a PR whose report cites
a rule and source URL for every change. Reviewers can talk to it on the PR with `@bumpless`.

## How the sponsor technology is used

- **Nebius Token Factory:** all inference, through the OpenAI-compatible API, with per-call cost tracking and
  per-run caps.
- **Nemotron 3 Nano / Super / Ultra:** tiered routing by task, with escalation on failure. The benchmark compares
  tiered routing to all-Ultra on the same repos (see the README Results).
- **Tavily:** search (raw markdown content), extract and map to find and read official migration guides and
  changelogs. Every rule cites a Tavily-fetched page, and a Nano check confirms the page supports it.

## Results

See README → Results (generated from stored benchmark runs; fixture repos).

## Honest limits

See README → Status and limits.
