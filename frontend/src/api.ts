export type Tier = "nano" | "super" | "ultra";

export interface Fixture { id: string; package: string; target: string; title: string; description: string }

export interface RunEvent { id: number; ts: number; type: string; data: Record<string, any> }

export interface Rule {
  id: string; title: string; old_pattern: string; new_pattern: string; notes: string;
  source_url: string; source_official: boolean; verified: boolean; confidence: number; learned_from_run?: string | null;
}

export interface CovHunk {
  path: string; start: number; end: number; added: string[]; removed: string[];
  confidence: "High" | "Medium" | "Low"; reasons: string[]; rule_id: string | null; source_url: string | null;
  verified: boolean; model_tier: Tier | null; escalated: boolean; repaired: boolean;
}

export interface TestSummary { passed: number; failed: number; skipped: number; total: number; failing: string[] }

export interface RunResult {
  run_id: string; status: "green" | "partial" | "failed"; error: string | null; package: string; target: string;
  routing: string; executor: string; old_version: string; new_version: string;
  tests: { old?: TestSummary; new_before?: TestSummary; after?: TestSummary };
  rulebook: { package: string; from: string; to: string; recipe_version: number; official_pages: number; checked_at: string; rules: Rule[] } | null;
  recipe_reused: boolean;
  characterization: { observations: number; old?: TestSummary; new_before?: TestSummary };
  coverage: { measured: boolean; percent: number | null; executed_changed_lines: number; executable_changed_lines: number;
    hunks: CovHunk[]; by_confidence: Record<string, number> };
  review: { approve: boolean; summary: string; violations: string[]; concerns: { path: string; issue: string }[] };
  escalations: { path: string; tier: Tier; reason: string }[];
  manual_review: string[];
  cost: { total_usd: number; by_tier: Record<Tier, number>; llm_calls: number };
  tavily: { calls: number; by_kind: Record<string, number>;
    log: { kind: string; query: string; results: number; cached: boolean; urls: string[]; rules: string[] }[] };
  duration_s: number;
  output: { branch?: string; pr_url?: string | null; pr_skipped_reason?: string | null };
}

export interface RunRow { id: string; created_at: number; repo: string; package: string; target: string; routing: string; status: string }

export interface RunInfo { id: string; status: string; package: string; target: string; routing: string; created_at: number; result: RunResult | null }

export interface Recipe {
  recipe: string; package: string; from: string; to: string; recipe_version: number; rules: number; verified_rules: number;
  checked_at: string; runs: number; success_rate: number | null; avg_first_run_cost: number | null;
  avg_reused_run_cost: number | null; path: string;
}

export interface BenchRow {
  name: string; kind: string; package: string; run_id: string; status: "green" | "partial" | "failed"; error: string | null;
  old_version: string | null; new_version: string | null; tests_failing_before_fix: number; tests_fixed: number;
  characterization_observations: number; characterization_pass_rate: number | null; coverage_percent: number | null;
  duration_s: number; cost_usd: number; cost_by_tier: Record<string, number>; escalations: number; recipe_reused: boolean;
  manual_review: number;
}

export interface BenchSummary {
  repos: number; green: number; partial: number; failed: number; success_rate: number | null; tests_fixed: number;
  tests_failing_before_fix: number; median_characterization_pass_rate: number | null; median_coverage_percent: number | null;
  median_duration_s: number | null; median_cost_usd: number | null; total_cost_usd: number; escalations: number;
}

export interface BenchResult { bench_id: string; routing: string; created_at: number; summary: BenchSummary; runs: BenchRow[] }

export interface RadarRow {
  package: string; spec: string; current: string; latest: string; majors_behind: number; files: number; references: number;
  recipe: { version: number; rules: number; verified: number } | null; target: string; risk: string; risk_reason: string;
  estimate: { usd: number | null; basis: string };
}

export interface Replay {
  id: string; title: string; status: string; package: string; created_at: number; cost_usd: number | null;
  duration_s: number | null; coverage: number | null; tests: TestSummary | null;
}

export interface Status {
  token_factory: { ok: boolean; error: string | null; models: Record<string, { model: string; ok: boolean }> };
  tavily: { ok: boolean; error: string | null };
  budget: { daily_usd: number; spent_today_usd: number; remaining_usd: number };
  last_successful_run: { id: string; created_at: number; package: string } | null;
  replays: number; password_required: boolean;
  live: { available: boolean; reason: string | null };
}

export interface CommentReply {
  acted: boolean; intent: string | null; reply: string | null; files?: string[]; commit?: string | null;
  diff?: string; cost_usd?: number; tests?: TestSummary;
}

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init);
  if (!r.ok) {
    let msg = `Request failed (${r.status})`;
    try { msg = (await r.json()).detail ?? msg; } catch { /* not JSON */ }
    throw new Error(msg);
  }
  return r.headers.get("content-type")?.includes("json") ? r.json() : (r.text() as Promise<T>);
}

export const api = {
  fixtures: () => req<Fixture[]>("/api/fixtures"),
  runs: () => req<RunRow[]>("/api/runs"),
  run: (id: string) => req<RunInfo>(`/api/runs/${id}`),
  report: (id: string) => req<string>(`/api/runs/${id}/report`),
  recipes: () => req<Recipe[]>("/api/recipes"),
  bench: () => req<BenchResult[]>("/api/bench"),
  replays: () => req<Replay[]>("/api/replays"),
  replay: (id: string) => req<RunInfo & { recorded_at: number }>(`/api/replays/${id}`),
  status: () => req<Status>("/api/status"),
  comment: (id: string, body: string, association: string, password = "") =>
    req<CommentReply>(`/api/runs/${id}/comment`, { method: "POST", headers: { "Content-Type": "application/json", "X-Demo-Password": password }, body: JSON.stringify({ body, association }) }),
  radar: (fixture: string) =>
    req<{ source: string; rows: RadarRow[] }>("/api/radar", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ fixture }) }),
  start: (body: { fixture?: string; repo?: string; package: string; target: string; routing: string }, password = "") =>
    req<{ run_id: string }>("/api/runs", { method: "POST", headers: { "Content-Type": "application/json", "X-Demo-Password": password }, body: JSON.stringify(body) }),
};

export const money = (v: number | null | undefined, digits = 4) => (v == null ? "—" : `$${v.toFixed(digits)}`);
