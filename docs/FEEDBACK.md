# Feedback: Token Factory, Nemotron, Tavily, Nebius Serverless

Notes collected while building Bumpless. Concrete and dated.

## Token Factory
- 2026-10-27: OpenAI-compatible API worked first try with the `openai` SDK (`base_url` + key). `GET /v1/models` lists all three Nemotron 3 tiers.
- Model ID casing is inconsistent across the family (`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, `nvidia/nemotron-3-super-120b-a12b`, `nvidia/Nemotron-3-Ultra-550b-a55b`). Easy to typo; a case-insensitive lookup or consistent naming would help.

## Nemotron 3
- 2026-10-27: Nano spent 56 completion tokens (reasoning) to answer "OK" and had ~7s first-call latency; Super/Ultra answered in 24 tokens, <1s.

## Tavily

## Nebius Serverless
