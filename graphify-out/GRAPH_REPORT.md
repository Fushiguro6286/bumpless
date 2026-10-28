# Graph Report - Nebius x NVIDIA Global AI Hackathon  (2026-10-28)

## Corpus Check
- 194 files · ~97,697 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: (none) 7, .example 1, .css 1)

## Summary
- 1484 nodes · 3272 edges · 102 communities (81 shown, 21 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 234 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Frontend API Client
- OpenAI Fixture LLM Client
- Benchmark Fixture Repos
- Migration Prompt Pipeline
- Dependabot Workflow
- Run Context and Error Learning
- Frontend Dependencies
- Static Import Scan
- Benchmark Charts and Results
- Orders Fixture Models
- SQLAlchemy Notes Fixture
- Inventory Fixture Catalog
- API Routes
- Rule Source Verification
- Per-File Edit Engine
- Characterization Tests
- Pin Bump Intake
- CLI Commands
- Prompts and Schemas
- Pydantic App Models
- Sandbox Executor Interface
- Recipe Store
- Tavily Search Cache
- LLM Client Wrapper
- Baseline Test Runs
- TS App Config
- Pydantic App Tests
- Probe Guardrails
- Verified Change Coverage
- Repair and File IO
- GitHub PR Helpers
- Action Inputs Wiring
- TS Node Config
- Pydantic App Service
- Demo Repo Service
- PR Conversation Handler
- Action Env Vars
- User Storage Modules
- Executor Test Fakes
- Demo Repo Tests
- FastAPI App and Docker
- Runs and Bench API
- Replay Recordings
- Token Factory Client
- Action Input Defs
- Summarize Fixture
- Comment Env Vars
- Render Deploy Config
- Migrate Action Manifest
- Comment Action Manifest
- Comment Action Inputs
- Probe Harness Observer
- Model Pricing
- Action Run Steps
- Bumpless Workflow
- Comment Steps
- Test Workflow
- Dependabot Config
- Workflow Dispatch Inputs
- Settings and Env
- Benchmark Repo List
- Run Events Bus
- Model Tier Router
- Docker Executor
- SQLite Storage
- Comment Respond Job
- Oxlint Config
- Action Input 67
- Action Input 68
- Action Input 69
- Action Input 70
- Action Input 71
- Action Input 72
- Action Input 73
- Action Input 74
- Action Input 75
- Action Input 76
- Cost Chart
- Success Rate Chart
- JSON Parsing Helpers
- Workflow Triggers
- Action Input 81
- Action Input 82
- Action Input 83
- Action Input 84
- Action Input 85
- TS Root Config
- Brand Logo
- Schema Output Model
- Bumpless Package

## God Nodes (most connected - your core abstractions)
1. `RunContext` - 71 edges
2. `run_migration()` - 45 edges
3. `Rule` - 35 edges
4. `Card()` - 29 edges
5. `LLM` - 26 edges
6. `edit_file()` - 25 edges
7. `money()` - 21 edges
8. `Rulebook` - 20 edges
9. `ErrorBox()` - 20 edges
10. `handle()` - 18 edges

## Surprising Connections (you probably didn't know these)
- `chat()` --indirect_call--> `e()`  [INFERRED]
  benchmarks/fixtures/openai_app/app/llm.py → bumpless/settings.py
- `review()` --indirect_call--> `e()`  [INFERRED]
  benchmarks/fixtures/openai_moderator/mod/pipeline.py → bumpless/settings.py
- `go()` --indirect_call--> `ctx()`  [INFERRED]
  bumpless/cli.py → tests/test_status.py
- `test_budget_cap()` --uses--> `BudgetExceeded`  [INFERRED]
  tests/test_llm.py → bumpless/llm/client.py
- `Tiered vs All-Ultra Comparison (29% cheaper, 5/5 vs 3/5)` --references--> `All-Ultra Routing Mode`  [INFERRED]
  benchmarks/RESULTS.md → README.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Bumpless Migration Pipeline (research -> characterize -> migrate -> verify -> learn -> talk)** — readme_research_step, readme_characterization_tests, readme_migrate_step, readme_docker_sandbox, readme_verified_change_coverage, readme_recipes, readme_pr_conversation [EXTRACTED 1.00]
- **Five Benchmarked Fixture Repos (37 broken tests)** — benchmarks_fixtures_pydantic_app_readme_pydantic_app, benchmarks_fixtures_pydantic_inventory_readme_pydantic_inventory, benchmarks_fixtures_pydantic_orders_readme_pydantic_orders, benchmarks_fixtures_openai_app_readme_openai_app, benchmarks_fixtures_openai_moderator_readme_openai_moderator [EXTRACTED 1.00]
- **Rule Trust Chain (Tavily source -> verified rule -> cited change)** — readme_tavily, readme_rulebook, readme_source_verification, readme_verified_change_coverage [INFERRED 0.85]
- **Research pipeline: summarize -> rulebook -> verify** — bumpless_llm_prompts_summarize_summarize_prompt, bumpless_llm_prompts_rulebook_rulebook_prompt, bumpless_llm_prompts_verify_rule_verify_rule_prompt, bumpless_llm_prompts_rulebook_migration_rule [INFERRED 0.85]
- **Migration execution: probe -> plan -> edit -> diagnose -> review** — bumpless_llm_prompts_probe_probe_prompt, bumpless_llm_prompts_plan_plan_prompt, bumpless_llm_prompts_edit_edit_prompt, bumpless_llm_prompts_diagnose_diagnose_prompt, bumpless_llm_prompts_review_review_prompt [INFERRED 0.85]
- **Sponsor stack: Token Factory + Nemotron 3 + Tavily** — docs_feedback_nebius_token_factory, docs_feedback_nemotron_3, docs_feedback_tavily, docs_submission_bumpless [EXTRACTED 1.00]
- **Tiered vs all-ultra cost comparison** — benchmarks_charts_cost_all_ultra, benchmarks_charts_cost_tiered, benchmarks_charts_cost_total_cost_usd [EXTRACTED 1.00]
- **Tiered vs all-ultra success comparison** — benchmarks_charts_success_tiered, benchmarks_charts_success_all_ultra, benchmarks_charts_success_success_rate_metric [EXTRACTED 1.00]

## Communities (102 total, 21 thin omitted)

### Community 0 - "Frontend API Client"
Cohesion: 0.05
Nodes (96): api, BenchResult, BenchRow, BenchSummary, CommentReply, CovHunk, Fixture, money() (+88 more)

### Community 1 - "OpenAI Fixture LLM Client"
Cohesion: 0.05
Nodes (29): chat(), LLMError, RateLimited, Handler, categories(), flagged(), ModerationUnavailable, suggest_reply() (+21 more)

### Community 2 - "Benchmark Fixture Repos"
Cohesion: 0.06
Nodes (46): Local Fake OpenAI-compatible Test Server, openai_app fixture, openai==0.28.1, openai_moderator fixture, openai==0.28.1, pydantic_app fixture, pydantic==1.10.18, pydantic_inventory fixture (+38 more)

### Community 3 - "Migration Prompt Pipeline"
Cohesion: 0.05
Nodes (41): Diagnose/Repair Prompt, Per-File Edit Prompt, SEARCH/REPLACE Edit Block (RULE_ID), Plan JSON (files, rule_ids, risk, notes, manual_review), Migration Plan Prompt, Static Scan Results (file -> rule ids), observe(name, lambda) Recorder, Characterization Probe Prompt (+33 more)

### Community 4 - "Dependabot Workflow"
Cohesion: 0.05
Nodes (48): if, runs-on, steps, ASSOCIATION, GH_TOKEN, PR, package, target (+40 more)

### Community 5 - "Run Context and Error Learning"
Cohesion: 0.13
Nodes (18): RunContext, commit(), step(), learn_from_error(), is_official(), official_sources(), project_info(), get_rulebook() (+10 more)

### Community 6 - "Frontend Dependencies"
Cohesion: 0.07
Nodes (34): dependencies, react@^19.3.1, react-dom@^19.3.1, react-router-dom@^7.18.4, recharts@^3.10.1, tailwindcss@^4.3.3, @tailwindcss/vite@^4.3.3, devDependencies (+26 more)

### Community 7 - "Static Import Scan"
Cohesion: 0.12
Nodes (15): imported_modules(), imports_package(), module_name(), python_files(), scan(), _tree(), usage_identifiers(), cost_estimate() (+7 more)

### Community 8 - "Benchmark Charts and Results"
Cohesion: 0.11
Nodes (21): charts(), fmt(), main(), pct(), provider(), status(), summary(), table() (+13 more)

### Community 9 - "Orders Fixture Models"
Cohesion: 0.14
Nodes (24): add_tag(), dump(), from_rows(), load(), order_schema(), reprice(), summary(), Line (+16 more)

### Community 10 - "SQLAlchemy Notes Fixture"
Cohesion: 0.18
Nodes (20): make_engine(), make_session(), Note, Notebook, add_note(), bulk_insert(), count_by_notebook(), get_note() (+12 more)

### Community 11 - "Inventory Fixture Catalog"
Cohesion: 0.17
Nodes (21): catalog_from_json(), catalog_json(), product_fields(), product_from_payload(), product_to_payload(), reprice(), Catalog, Money (+13 more)

### Community 12 - "API Routes"
Cohesion: 0.15
Nodes (15): _artifact(), CommentRequest, fixtures(), get_patch(), get_report(), list_fixtures(), live_blocker(), pr_comment() (+7 more)

### Community 13 - "Rule Source Verification"
Cohesion: 0.17
Nodes (18): Rule, api_tokens(), excerpt(), mentioned(), _occurs(), _squash(), Verdict, verify_rule() (+10 more)

### Community 14 - "Per-File Edit Engine"
Cohesion: 0.15
Nodes (17): apply_block(), apply_blocks(), Block, edit_all(), edit_file(), _indent(), new_errors(), parse_blocks() (+9 more)

### Community 15 - "Characterization Tests"
Cohesion: 0.11
Nodes (8): characterize(), extract_code(), _parse(), _run_probe(), source_files(), stable(), build_result(), tavily_usage()

### Community 16 - "Pin Bump Intake"
Cohesion: 0.15
Nodes (14): check(), go(), context_for(), PinRef, apply_pin_bumps(), bump_line(), find_pins(), install_commands() (+6 more)

### Community 17 - "CLI Commands"
Cohesion: 0.11
Nodes (9): bench(), comment(), go(), main(), _printer(), recipes_list(), record(), run() (+1 more)

### Community 18 - "Prompts and Schemas"
Cohesion: 0.15
Nodes (11): render(), Plan, PlanFile, RuleDrafts, plan(), rules_text(), check_final_diff(), Concern (+3 more)

### Community 19 - "Pydantic App Models"
Cohesion: 0.11
Nodes (8): Address, User, Config, UserUpdate, Address, User, Config, UserUpdate

### Community 20 - "Sandbox Executor Interface"
Cohesion: 0.12
Nodes (4): Executor, get_executor(), LocalExecutor, NebiusJobExecutor

### Community 21 - "Recipe Store"
Cohesion: 0.19
Nodes (13): Rulebook, age_days(), _key(), load(), merge(), path_for(), save(), stats() (+5 more)

### Community 22 - "Tavily Search Cache"
Cohesion: 0.19
Nodes (7): emit(), record_run(), _cache_get(), _cache_put(), _key(), Tavily, insert()

### Community 23 - "LLM Client Wrapper"
Cohesion: 0.20
Nodes (12): cost_usd(), LLM, LLMOutputError, assess(), FakeClient, test_budget_cap(), test_chat_json_gives_up(), test_chat_json_last_retry_goes_one_tier_up() (+4 more)

### Community 24 - "Baseline Test Runs"
Cohesion: 0.19
Nodes (13): _verify(), baseline(), install(), installed_version(), parse_junit(), run_tests(), TestRun, final_status() (+5 more)

### Community 25 - "TS App Config"
Cohesion: 0.10
Nodes (19): compilerOptions, allowArbitraryExtensions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection (+11 more)

### Community 26 - "Pydantic App Tests"
Cohesion: 0.16
Nodes (11): test_other_errors_map_to_llm_error(), test_rate_limit_maps_to_rate_limited(), make_user(), test_invalid_email_rejected(), test_json_roundtrip(), test_negative_age_rejected(), test_partial_update(), test_payload_excludes_none() (+3 more)

### Community 27 - "Probe Guardrails"
Cohesion: 0.16
Nodes (13): patches_package(), _calls_per_test(), guardrail_violations(), is_test_file(), _test_stats(), test_adding_skip_is_rejected(), test_api_migration_in_tests_is_allowed(), test_ci_and_secrets_rejected() (+5 more)

### Community 28 - "Verified Change Coverage"
Cohesion: 0.26
Nodes (12): Hunk, change_coverage(), confidence(), DiffHunk, measure(), parse_diff(), _provenance(), _ctx() (+4 more)

### Community 29 - "Repair and File IO"
Cohesion: 0.23
Nodes (10): read(), write(), _apply_repair(), _diagnose_prompt(), _field(), _full_files(), git_diff(), relevant_files() (+2 more)

### Community 30 - "GitHub PR Helpers"
Cohesion: 0.18
Nodes (9): can_push(), _client(), comment(), open_pr(), parse_repo(), repo_info(), render(), _tests() (+1 more)

### Community 31 - "Action Inputs Wiring"
Cohesion: 0.12
Nodes (17): with, association, base-ref, base-url, comment-body, fetch-depth, github-token, model-nano (+9 more)

### Community 32 - "TS Node Config"
Cohesion: 0.12
Nodes (16): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, noEmit, noFallthroughCasesInSwitch (+8 more)

### Community 33 - "Pydantic App Service"
Cohesion: 0.20
Nodes (8): apply_update(), parse_user_json(), parse_users(), roundtrip(), to_json(), to_payload(), user_from_row(), UserRow

### Community 34 - "Demo Repo Service"
Cohesion: 0.20
Nodes (8): apply_update(), parse_user_json(), parse_users(), roundtrip(), to_json(), to_payload(), user_from_row(), UserRow

### Community 35 - "PR Conversation Handler"
Cohesion: 0.22
Nodes (9): changed_files(), _commit(), _diff(), handle(), Intent, rebuild_workspace(), _result_lines(), Revision (+1 more)

### Community 36 - "Action Env Vars"
Cohesion: 0.13
Nodes (15): BASE_REF, EXECUTOR, GH_TOKEN, GITHUB_TOKEN, MODEL_NANO, MODEL_SUPER, MODEL_ULTRA, NEBIUS_API_KEY (+7 more)

### Community 37 - "User Storage Modules"
Cohesion: 0.21
Nodes (4): load_users(), save_users(), load_users(), save_users()

### Community 38 - "Executor Test Fakes"
Cohesion: 0.22
Nodes (7): ExecResult, ctx_for(), FakeExecutor, FakeLLM, repo_with_migration(), test_non_collaborators_and_non_trigger_are_ignored_without_model_calls(), test_revert_only_touches_the_named_file_and_commits()

### Community 39 - "Demo Repo Tests"
Cohesion: 0.21
Nodes (7): make_user(), test_invalid_email_rejected(), test_json_roundtrip(), test_negative_age_rejected(), test_partial_update(), test_payload_excludes_none(), test_strips_whitespace_and_lowercases_email()

### Community 41 - "Runs and Bench API"
Cohesion: 0.22
Nodes (10): get_replay(), get_run(), list_bench(), list_recipes(), list_runs(), replay_events(), stream_events(), gen() (+2 more)

### Community 42 - "Replay Recordings"
Cohesion: 0.23
Nodes (9): list_replays(), gen(), list_recordings(), paced(), public_event(), public_result(), record(), test_local_paths_are_scrubbed() (+1 more)

### Community 43 - "Token Factory Client"
Cohesion: 0.20
Nodes (6): doctor(), _doctor(), BudgetExceeded, check_models(), ModelConfigError, pricing()

### Community 44 - "Action Input Defs"
Cohesion: 0.15
Nodes (13): description, required, inputs, base-ref, nebius-api-key, package, target, description (+5 more)

### Community 45 - "Summarize Fixture"
Cohesion: 0.26
Nodes (5): bullet_points(), similarity(), summarize(), test_bullet_points_skip_rate_limited(), test_summarize_and_similarity()

### Community 46 - "Comment Env Vars"
Cohesion: 0.17
Nodes (12): ASSOCIATION, BODY, COMMENTER, EXECUTOR, GH_TOKEN, MODEL_NANO, MODEL_SUPER, MODEL_ULTRA (+4 more)

### Community 47 - "Render Deploy Config"
Cohesion: 0.18
Nodes (10): key, sync, value, services, envVars, healthCheckPath, name, plan (+2 more)

### Community 48 - "Migrate Action Manifest"
Cohesion: 0.20
Nodes (9): branding, color, icon, description, name, outputs, status, description (+1 more)

### Community 49 - "Comment Action Manifest"
Cohesion: 0.20
Nodes (9): description, name, runs, steps, using, name, run, shell (+1 more)

### Community 50 - "Comment Action Inputs"
Cohesion: 0.20
Nodes (10): description, required, description, required, inputs, association, github-token, pr-number (+2 more)

### Community 51 - "Probe Harness Observer"
Cohesion: 0.24
Nodes (3): category(), norm(), observe()

### Community 52 - "Model Pricing"
Cohesion: 0.20
Nodes (9): nano, input, output, super, input, output, ultra, input (+1 more)

### Community 53 - "Action Run Steps"
Cohesion: 0.22
Nodes (9): runs, steps, using, id, if, name, run, shell (+1 more)

### Community 54 - "Bumpless Workflow"
Cohesion: 0.22
Nodes (8): if, runs-on, jobs, bumpless, name, permissions, contents, pull-requests

### Community 55 - "Comment Steps"
Cohesion: 0.33
Nodes (9): steps, ASSOCIATION, steps, env, id, if, name, run (+1 more)

### Community 56 - "Test Workflow"
Cohesion: 0.22
Nodes (8): jobs, pytest, name, on, runs-on, steps, run, uses

### Community 57 - "Dependabot Config"
Cohesion: 0.25
Nodes (7): interval, updates, directory, open-pull-requests-limit, package-ecosystem, schedule, version

### Community 58 - "Workflow Dispatch Inputs"
Cohesion: 0.25
Nodes (8): package, target, workflow_dispatch, description, required, description, required, inputs

### Community 60 - "Benchmark Repo List"
Cohesion: 0.29
Nodes (6): repos, kind, name, package, source, to

### Community 62 - "Model Tier Router"
Cohesion: 0.29
Nodes (4): tier_for(), test_router_all_ultra(), test_router_rejects_unknown(), test_router_tiered_and_escalation()

### Community 65 - "Comment Respond Job"
Cohesion: 0.33
Nodes (6): GH_TOKEN, PR, respond, env, if, runs-on

### Community 66 - "Oxlint Config"
Cohesion: 0.33
Nodes (5): plugins, rules, react/only-export-components, react/rules-of-hooks, $schema

### Community 67 - "Action Input 67"
Cohesion: 0.50
Nodes (4): default, description, required, base-url

### Community 68 - "Action Input 68"
Cohesion: 0.50
Nodes (4): model-nano, default, description, required

### Community 69 - "Action Input 69"
Cohesion: 0.50
Nodes (4): model-super, default, description, required

### Community 70 - "Action Input 70"
Cohesion: 0.50
Nodes (4): model-ultra, default, description, required

### Community 71 - "Action Input 71"
Cohesion: 0.50
Nodes (4): pr-number, default, description, required

### Community 72 - "Action Input 72"
Cohesion: 0.50
Nodes (4): routing, default, description, required

### Community 73 - "Action Input 73"
Cohesion: 0.50
Nodes (4): default, description, required, base-url

### Community 74 - "Action Input 74"
Cohesion: 0.50
Nodes (4): model-nano, default, description, required

### Community 75 - "Action Input 75"
Cohesion: 0.50
Nodes (4): model-super, default, description, required

### Community 76 - "Action Input 76"
Cohesion: 0.50
Nodes (4): model-ultra, default, description, required

### Community 77 - "Cost Chart"
Cohesion: 0.67
Nodes (4): all-ultra strategy ($0.564), Total Cost Comparison Chart (all-ultra vs tiered), tiered strategy ($0.398), Total cost (USD) metric

### Community 78 - "Success Rate Chart"
Cohesion: 0.67
Nodes (4): All-ultra strategy (60% success), Success Rate Chart (% green), Success rate (% green), Tiered strategy (100% success)

### Community 79 - "JSON Parsing Helpers"
Cohesion: 0.67
Nodes (3): parse_json(), strip_reasoning(), test_strip_and_parse()

### Community 80 - "Workflow Triggers"
Cohesion: 0.50
Nodes (4): types, on, issue_comment, pull_request

### Community 81 - "Action Input 81"
Cohesion: 0.67
Nodes (3): description, required, github-token

### Community 82 - "Action Input 82"
Cohesion: 0.67
Nodes (3): tavily-api-key, description, required

### Community 83 - "Action Input 83"
Cohesion: 0.67
Nodes (3): description, required, comment-body

### Community 84 - "Action Input 84"
Cohesion: 0.67
Nodes (3): nebius-api-key, description, required

### Community 85 - "Action Input 85"
Cohesion: 0.67
Nodes (3): user, description, required

## Knowledge Gaps
- **22 isolated node(s):** `bumpless`, `Per-run Cost Tracking and Cap (MAX_RUN_COST_USD, config/pricing.yaml)`, `bumpless doctor`, `openai==0.28.1`, `openai==0.28.1` (+17 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 530 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **21 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `run_migration()` connect `Pin Bump Intake` to `Run Context and Error Learning`, `Static Import Scan`, `Benchmark Charts and Results`, `API Routes`, `Per-File Edit Engine`, `Characterization Tests`, `CLI Commands`, `Prompts and Schemas`, `Sandbox Executor Interface`, `Recipe Store`, `Tavily Search Cache`, `LLM Client Wrapper`, `Baseline Test Runs`, `Verified Change Coverage`, `Repair and File IO`, `GitHub PR Helpers`, `User Storage Modules`, `Token Factory Client`, `SQLite Storage`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Are the 47 inferred relationships involving `RunContext` (e.g. with `_commit()` and `handle()`) actually correct?**
  _`RunContext` has 47 INFERRED edges - model-reasoned connections that need verification._
- **What connects `bumpless`, `Per-run Cost Tracking and Cap (MAX_RUN_COST_USD, config/pricing.yaml)`, `bumpless doctor` to the rest of the system?**
  _22 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Frontend API Client` be split into smaller, more focused modules?**
  _Cohesion score 0.054835493519441676 - nodes in this community are weakly interconnected._
- **Why does `RunContext` connect `Run Context and Error Learning` to `PR Conversation Handler`, `Executor Test Fakes`, `Rule Source Verification`, `Per-File Edit Engine`, `Characterization Tests`, `Pin Bump Intake`, `Prompts and Schemas`, `Sandbox Executor Interface`, `Recipe Store`, `Tavily Search Cache`, `LLM Client Wrapper`, `Baseline Test Runs`, `Verified Change Coverage`, `Repair and File IO`, `GitHub PR Helpers`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `run_migration()` (e.g. with `BudgetExceeded` and `.emit()`) actually correct?**
  _`run_migration()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Should `OpenAI Fixture LLM Client` be split into smaller, more focused modules?**
  _Cohesion score 0.052464947987336044 - nodes in this community are weakly interconnected._