import { useEffect, useMemo, useReducer, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, money, type RunEvent, type RunInfo, type Tier } from "../api";
import { Card, ErrorBox, SourceChip, StatusPill, TierBadge, TIER_COLOR, TIER_LABEL, VerifiedBadge } from "../components/ui";
import { initialState, reduce, STEPS, type LiveState } from "../runState";
import Result from "./Result";

type Action = { ev: RunEvent } | { reset: true };

export function reducer(s: LiveState, a: Action) {
  return "reset" in a ? initialState() : reduce(s, a.ev);
}

/** Subscribe to the run's SSE stream (history first, then live). `replay` streams a recording instead. */
export function useRunEvents(url: string | null, dispatch: (a: Action) => void) {
  useEffect(() => {
    if (!url) return;
    dispatch({ reset: true });
    const es = new EventSource(url);
    es.onmessage = (m) => {
      const ev = JSON.parse(m.data) as RunEvent;
      dispatch({ ev });
      if (ev.type === "run_finished") es.close();
    };
    es.onerror = () => { /* EventSource retries on its own; the server resumes from history */ };
    return () => es.close();
  }, [url, dispatch]);
}

export default function Run() {
  const { id = "" } = useParams();
  const [state, dispatch] = useReducer(reducer, undefined, initialState);
  const [info, setInfo] = useState<RunInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  useRunEvents(`/api/runs/${id}/events`, dispatch);

  useEffect(() => {
    api.run(id).then(setInfo).catch((e) => setError(e.message));
  }, [id]);
  useEffect(() => {
    if (state.finished) api.run(id).then(setInfo).catch(() => {});
  }, [state.finished, id]);

  if (error) return <ErrorBox>Could not load this run: {error}</ErrorBox>;
  return <RunView state={state} result={info?.result ?? null} title={info ? `${info.package}${info.target}` : ""} runId={id} />;
}

export function RunView({ state, result, title, runId, banner }: {
  state: LiveState; result: RunInfo["result"]; title: string; runId: string; banner?: React.ReactNode;
}) {
  const status = state.finished?.status ?? (result ? result.status : "running");
  return (
    <div className="space-y-6">
      {banner}
      <div className="flex flex-wrap items-center gap-3">
        <Link to="/runs" className="text-sm text-ink-400 hover:text-ink-100">← Runs</Link>
        <h1 className="text-2xl font-semibold tracking-tight">{state.meta.source?.replace(/\\/g, "/").split("/").pop() ?? "Run"}</h1>
        <code className="rounded bg-ink-800 px-2 py-0.5 text-sm text-ink-300">{state.meta.package ?? ""}{state.meta.target ?? title}</code>
        <StatusPill status={status} />
        <span className="text-xs text-ink-400">run {runId}{state.meta.routing ? ` · ${state.meta.routing} routing` : ""}</span>
      </div>
      {state.error && <ErrorBox>{state.error}</ErrorBox>}
      {result && state.finished && <Result r={result} runId={runId} />}
      <Live state={state} />
    </div>
  );
}

function Live({ state }: { state: LiveState }) {
  const done = !!state.finished;
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
      <Card title={done ? "Timeline" : "Live run"} right={!done && <span className="flex items-center gap-2 text-xs text-sky-300"><span className="size-2 animate-pulse rounded-full bg-sky-400" />streaming</span>}>
        <ol className="relative space-y-1">
          {STEPS.map((s, i) => <StepRow key={s.id} idx={i} step={s} state={state} />)}
        </ol>
      </Card>
      <div className="space-y-6">
        <CostMeter state={state} />
        <TestsCard state={state} />
        <SourcesCard state={state} />
      </div>
    </div>
  );
}

function StepRow({ idx, step, state }: { idx: number; step: (typeof STEPS)[number]; state: LiveState }) {
  const st = state.steps[step.id];
  const [open, setOpen] = useState(false);
  const running = st.status === "running";
  const icon = { pending: "bg-ink-700", running: "bg-sky-400 animate-pulse", done: "bg-accent", error: "bg-rose-400" }[st.status];
  const expanded = running || open;
  const msgs = st.messages;
  return (
    <li className="rounded-lg border border-transparent px-2 py-2 hover:border-ink-700">
      <button className="flex w-full items-center gap-3 text-left" onClick={() => setOpen(!open)} aria-expanded={expanded} disabled={st.status === "pending"}>
        <span className={`size-2.5 shrink-0 rounded-full ${icon}`} aria-hidden />
        <span className="w-5 text-xs tabular-nums text-ink-400">{idx + 1}</span>
        <span className={`font-medium ${st.status === "pending" ? "text-ink-400" : ""}`}>{step.label}</span>
        <span className="hidden truncate text-xs text-ink-400 sm:inline">{step.hint}</span>
        <span className="ml-auto text-xs tabular-nums text-ink-400">
          {st.status === "done" && st.duration != null ? `${st.duration.toFixed(1)}s` : st.status === "running" ? "running…" : st.status === "error" ? "error" : ""}
        </span>
      </button>
      {expanded && msgs.length > 0 && (
        <ul className="mt-2 space-y-1 border-l border-ink-700 pl-5 ml-[5px]">
          {msgs.map((m, i) => (
            <li key={i} className={`text-sm ${m.kind === "escalation" ? "text-amber-300" : m.kind === "learned" ? "text-violet-300" : "text-ink-300"}`}>
              {m.kind === "escalation" && "↑ "}{m.text}
            </li>
          ))}
        </ul>
      )}
      {expanded && step.id === "research" && state.rules.length > 0 && <RulesLive state={state} />}
      {expanded && step.id === "edit" && Object.keys(state.files).length > 0 && <FilesLive state={state} />}
    </li>
  );
}

function RulesLive({ state }: { state: LiveState }) {
  return (
    <div className="mt-3 ml-[5px] space-y-1.5 border-l border-ink-700 pl-5">
      {state.recipeReused && <div className="text-xs text-accent">Recipe reused: {state.recipeReused}</div>}
      {state.rules.map((r) => (
        <div key={r.id} className="flex flex-wrap items-center gap-2 text-sm">
          <code className="text-xs text-ink-400">{r.id}</code>
          <span className={r.verified ? "" : "text-ink-400 line-through decoration-rose-400/60"}>{r.title}</span>
          <VerifiedBadge ok={r.verified} />
        </div>
      ))}
    </div>
  );
}

function FilesLive({ state }: { state: LiveState }) {
  return (
    <div className="mt-3 ml-[5px] grid gap-1.5 border-l border-ink-700 pl-5">
      {Object.values(state.files).map((f) => (
        <div key={f.path} className="flex flex-wrap items-center gap-2 text-sm">
          <code className="text-xs">{f.path}</code>
          {f.escalations.length > 0 ? <>{["nano" as Tier, ...f.escalations].map((t, i) => <span key={i} className="flex items-center gap-1">{i > 0 && <span className="text-amber-300">→</span>}<TierBadge tier={t} /></span>)}</> : <TierBadge tier={f.tier} />}
          <span className={`text-xs ${f.failed ? "text-rose-300" : "text-ink-400"}`}>
            {f.failed ? "edit failed: needs review" : f.edits === 0 ? "no changes needed" : f.edits != null ? `${f.edits} edits` : "editing…"}
          </span>
        </div>
      ))}
    </div>
  );
}

function CostMeter({ state }: { state: LiveState }) {
  const tiers: Tier[] = ["nano", "super", "ultra"];
  const total = tiers.reduce((a, t) => a + state.cost[t], 0) || 1;
  return (
    <Card title="Cost meter" right={<span className="text-xs text-ink-400">{state.llmCalls} LLM calls</span>}>
      <div className="text-3xl font-semibold tabular-nums">{money(state.total)}</div>
      <div className="mt-3 flex h-2.5 overflow-hidden rounded-full bg-ink-700" role="img" aria-label="Cost split by model tier">
        {tiers.map((t) => <div key={t} style={{ width: `${(100 * state.cost[t]) / total}%`, background: TIER_COLOR[t] }} />)}
      </div>
      <dl className="mt-3 grid grid-cols-3 gap-2 text-xs">
        {tiers.map((t) => (
          <div key={t}><dt className="flex items-center gap-1.5 text-ink-400"><span className="size-2 rounded-full" style={{ background: TIER_COLOR[t] }} />{TIER_LABEL[t]}</dt>
            <dd className="mt-0.5 tabular-nums">{money(state.cost[t])}</dd></div>
        ))}
      </dl>
    </Card>
  );
}

function TestsCard({ state }: { state: LiveState }) {
  if (state.tests.length === 0) return null;
  return (
    <Card title="Tests">
      <ul className="space-y-2">
        {state.tests.map((x, i) => {
          const red = x.t.failed > 0;
          return (
            <li key={i} className="flex items-center justify-between gap-2 text-sm">
              <span className="text-ink-300">{x.label}</span>
              <span className="tabular-nums">
                <span className="text-emerald-300">{x.t.passed} ✓</span>
                <span className={`ml-2 ${red ? "text-rose-300" : "text-ink-400"}`}>{x.t.failed} ✗</span>
              </span>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

function SourcesCard({ state }: { state: LiveState }) {
  const official = useMemo(() => state.pages.filter((p) => p.official).length, [state.pages]);
  if (state.pages.length === 0 && state.tavily.length === 0) return null;
  return (
    <Card title="Tavily sources" right={<span className="text-xs text-ink-400">{state.tavily.length} calls</span>}>
      {state.pages.length > 0 && <p className="mb-2 text-xs text-ink-400">{state.pages.length} pages fetched, {official} official{state.officialPages ? ` · rulebook built from ${state.officialPages} official pages` : ""}</p>}
      <div className="flex flex-wrap gap-1.5">
        {state.pages.slice(0, 18).map((p) => <SourceChip key={p.url} url={p.url} official={p.official} />)}
      </div>
    </Card>
  );
}
