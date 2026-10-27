# Feedback: Token Factory, Nemotron, Tavily, Nebius Serverless

Notes collected while building Bumpless. Concrete and dated.

## Token Factory
- 2026-10-27: OpenAI-compatible API worked first try with the `openai` SDK (`base_url` + key). `GET /v1/models` lists all three Nemotron 3 tiers.
- Model ID casing is inconsistent across the family (`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, `nvidia/nemotron-3-super-120b-a12b`, `nvidia/Nemotron-3-Ultra-550b-a55b`). Easy to typo; a case-insensitive lookup or consistent naming would help.

## Nemotron 3
- 2026-10-27: Nano spent 56 completion tokens (reasoning) to answer "OK" and had ~7s first-call latency; Super/Ultra answered in 24 tokens, <1s.

## Tavily

## Nebius Serverless

## Tavily (2026-10-27)
- `search(include_raw_content="markdown")` saves a separate `extract` call per result; very handy.
- `map` on a docs site needs the right section: mapping `pydantic.dev` returned 2 URLs; scoping with `select_paths`
  and climbing up a folder when the section is small fixed it. A "map the section this page belongs to" option would help.
- Search for "pydantic changelog" surfaced the *Pydantic AI* changelog on the same official domain. Domain filters
  can't separate sibling products; we added an "is this page about package X" check in our Nano verifier.

## Nemotron 3 (2026-10-27)
- Nano occasionally degenerates (16,000 completion tokens of repetition) on code-edit prompts; a repetition
  penalty or a lower default max_tokens would help. Our escalation to Super/Ultra recovers.
- Nano answering from memory about pydantic v2 invented changes ("Field aliases now always replace...").
  Grounding every rule in a fetched page is necessary, not optional.
