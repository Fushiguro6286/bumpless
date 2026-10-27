# Feedback: Token Factory, Nemotron, Tavily, Nebius Serverless

Notes collected while building Bumpless. Concrete and dated.

## Token Factory
- 2026-10-27: OpenAI-compatible API worked first try with the `openai` SDK (`base_url` + key). `GET /v1/models` lists all three Nemotron 3 tiers.
- Model ID casing is inconsistent across the family (`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, `nvidia/nemotron-3-super-120b-a12b`, `nvidia/Nemotron-3-Ultra-550b-a55b`). Easy to typo; a case-insensitive lookup or consistent naming would help.

## Nemotron 3
- 2026-10-27: Nano spent 56 completion tokens (reasoning) to answer "OK" and had ~7s first-call latency; Super/Ultra answered in 24 tokens, <1s.

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
- Nano (reasoning on or off) answered `NONE` ("no breaking changes") for every 40k-char chunk of the official
  openai v1 migration guide (a GitHub Discussion whose body arrives as one huge Markdown table cell). Super
  (reasoning off) extracted precise OLD/NEW code from the same chunk for ~$0.005. We now re-read official guide
  pages one tier up when Nano finds nothing. A "this content is long/structured, consider a bigger model" signal,
  or Nano robustness to table-wrapped prose, would help.
- With reasoning off, Super/Nano are fast and good at extraction tasks; `chat_template_kwargs.enable_thinking=false`
  cut our research step from 236 s to 137 s. Worth documenting prominently on Token Factory.

## Tavily (2026-10-27, later)
- GitHub Discussions pages come back with lots of UI boilerplate ("Uh oh! There was an error while loading.
  Please reload this page." repeated, `{{title}}` template placeholders) and the post body flattened into a table
  cell. Stripping known GitHub chrome in `raw_content` would make these pages much easier for models to use.
- Results are only as official as the domain filter: `include_domains=["github.com"]` for "openai migration guide"
  returned community repos alongside `openai/openai-python/discussions/742`; we rank by the package's own
  repo prefix from PyPI metadata.

## Nemotron 3 (2026-10-27, PR conversation)
- Super classified free-text review comments ("revert the change to app/storage.py") into a strict JSON intent
  for ~$0.0002 per comment, correctly in all three live tests (revert, explain, revise). Ultra explaining a diff against the rulebook cited rule IDs and
  said which edits were *not* rulebook-driven, without being asked to.

## Nebius Serverless
- Not tried yet (deploy and Jobs executor pending).

## Nemotron 3 (2026-10-27, zero-shot SQLAlchemy)
- With reasoning off, an "if nothing applies, reply exactly NONE" escape hatch was a strong attractor: on the same
  40k-char chunk of the SQLAlchemy 2.0 migration guide (full of before/after code), Nano and Super replied `NONE`
  in 8 of 9 tries. Rewording to "guides usually describe many changes: list every one; NONE only for a page with
  no upgrade content" gave 5/5 correct extractions. This is likely also why Nano "found nothing" on the openai
  guide earlier. Worth a note in the Nemotron prompting guide.

## Tavily (2026-10-27, zero-shot SQLAlchemy)
- `map` on `docs.sqlalchemy.org/en/latest/changelog/` (http or https, `select_paths` scoped to the section)
  returned 0 URLs, while `search` returned pages from that exact section. Possibly the `/en/latest/` redirect.
