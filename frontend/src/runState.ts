import type { Rule, RunEvent, TestSummary, Tier } from "./api";

export const STEPS = [
  { id: "intake", label: "Intake", hint: "Clone the repo, find version pins" },
  { id: "baseline", label: "Baseline", hint: "Tests on the old version, then the Dependabot red" },
  { id: "research", label: "Research", hint: "Tavily search, map and extract of official docs" },
  { id: "characterize", label: "Characterize", hint: "Record current behavior as golden tests" },
  { id: "plan", label: "Plan", hint: "Nemotron Ultra orders the migration" },
  { id: "edit", label: "Edit", hint: "Parallel Nano edits, escalating on failure" },
  { id: "verify", label: "Verify & repair", hint: "Sandboxed tests; Ultra repairs failures" },
  { id: "coverage", label: "Coverage", hint: "Which changed lines did tests execute?" },
  { id: "review", label: "Review", hint: "Guardrails + Ultra review" },
  { id: "output", label: "PR", hint: "Branch, report, pull request or patch" },
  { id: "learn", label: "Learn", hint: "Save the verified rulebook as a recipe" },
] as const;

export type StepStatus = "pending" | "running" | "done" | "error";

export interface StepState { status: StepStatus; duration?: number; messages: { ts: number; text: string; kind?: string }[] }

export interface EditFile { path: string; tier: Tier | null; edits: number | null; failed: boolean; escalations: Tier[] }

export interface LiveState {
  steps: Record<string, StepState>;
  current: string | null;
  cost: Record<Tier, number>;
  total: number;
  llmCalls: number;
  tavily: { kind: string; query: string; n: number; cached: boolean }[];
  pages: { url: string; official: boolean }[];
  rules: Rule[];
  officialPages: number;
  recipeReused: string | null;
  files: Record<string, EditFile>;
  tests: { label: string; t: TestSummary }[];
  finished: { status: string; error: string | null } | null;
  error: string | null;
  meta: { package?: string; target?: string; routing?: string; executor?: string; source?: string };
}

export const initialState = (): LiveState => ({
  steps: Object.fromEntries(STEPS.map((s) => [s.id, { status: "pending", messages: [] }])),
  current: null, cost: { nano: 0, super: 0, ultra: 0 }, total: 0, llmCalls: 0, tavily: [], pages: [], rules: [],
  officialPages: 0, recipeReused: null, files: {}, tests: [], finished: null, error: null, meta: {},
});

const clone = (s: LiveState): LiveState => ({
  ...s, steps: { ...s.steps }, cost: { ...s.cost }, files: { ...s.files }, tavily: [...s.tavily], tests: [...s.tests],
});

function addMsg(s: LiveState, step: string, ts: number, text: string, kind?: string) {
  const st = s.steps[step] ?? { status: "running", messages: [] };
  s.steps[step] = { ...st, messages: [...st.messages, { ts, text, kind }] };
}

export function reduce(prev: LiveState, ev: RunEvent): LiveState {
  const s = clone(prev);
  const d = ev.data;
  switch (ev.type) {
    case "run_started":
      s.meta = d;
      break;
    case "step_started":
      s.current = d.step;
      s.steps[d.step] = { ...(s.steps[d.step] ?? { messages: [] }), status: "running" };
      break;
    case "step_finished":
      s.steps[d.step] = { ...s.steps[d.step], status: "done", duration: d.duration_s };
      break;
    case "progress": {
      addMsg(s, d.step, ev.ts, d.message);
      if (d.pages) s.pages = d.pages;
      if (d.tests) {
        const label = d.step === "baseline" ? (s.tests.length === 0 ? "Old version" : "New version, before fix")
          : `Repair iteration ${d.iteration ?? 0}`;
        s.tests.push({ label, t: d.tests });
      }
      if (d.step === "edit" && d.path) {
        const f = s.files[d.path] ?? { path: d.path, tier: null, edits: null, failed: false, escalations: [] };
        s.files[d.path] = { ...f, tier: d.tier ?? f.tier, edits: d.edits ?? (d.failed ? null : 0), failed: !!d.failed };
      }
      break;
    }
    case "escalation": {
      addMsg(s, d.step, ev.ts, d.message, "escalation");
      const f = s.files[d.path] ?? { path: d.path, tier: null, edits: null, failed: false, escalations: [] };
      s.files[d.path] = { ...f, escalations: [...f.escalations, d.tier] };
      break;
    }
    case "llm_call":
      s.cost[d.tier as Tier] += d.cost_usd;
      s.total = d.run_total_usd;
      s.llmCalls += 1;
      if (d.step === "edit" && d.task === "edit") {
        // a file is "in progress" until its progress message arrives; nothing to do here
      }
      break;
    case "tavily_call":
      s.tavily.push({ kind: d.kind, query: d.query, n: d.n_results, cached: !!d.cached });
      break;
    case "rulebook":
      s.rules = d.rulebook.rules;
      s.officialPages = d.rulebook.official_pages;
      break;
    case "rules_learned":
      s.rules = [...s.rules, ...d.rules];
      addMsg(s, "verify", ev.ts, `Learned ${d.rules.length} new rule(s) from a Tavily lookup`, "learned");
      break;
    case "recipe_reused":
      s.recipeReused = `${d.recipe} v${d.recipe_version}`;
      break;
    case "error":
      s.error = d.message;
      if (s.current) s.steps[s.current] = { ...s.steps[s.current], status: "error" };
      break;
    case "run_finished":
      s.finished = { status: d.status, error: d.error };
      s.total = d.cost_usd;
      break;
  }
  return s;
}
