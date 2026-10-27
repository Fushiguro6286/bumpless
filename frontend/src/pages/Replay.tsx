import { useEffect, useReducer, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api, money, type Replay, type RunInfo } from "../api";
import { Card, ErrorBox, StatusPill } from "../components/ui";
import { initialState } from "../runState";
import { reducer, RunView, useRunEvents } from "./Run";

const SPEEDS = [1, 4, 16];

export default function ReplayPage() {
  const { id = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const speed = SPEEDS.includes(Number(params.get("speed"))) ? Number(params.get("speed")) : 1;
  const [state, dispatch] = useReducer(reducer, undefined, initialState);
  const [info, setInfo] = useState<(RunInfo & { recorded_at: number }) | null>(null);
  const [error, setError] = useState<string | null>(null);
  useRunEvents(`/api/replays/${id}/events?speed=${speed}`, dispatch);
  useEffect(() => { api.replay(id).then(setInfo).catch((e) => setError(e.message)); }, [id]);

  if (error) return <ErrorBox>Could not load this recording: {error}</ErrorBox>;
  const recorded = info ? new Date(info.created_at * 1000).toLocaleString() : "";
  const banner = (
    <div role="status" className="flex flex-wrap items-center gap-3 rounded-lg border border-sky-500/40 bg-sky-500/10 px-4 py-3 text-sm text-sky-200">
      <span className="font-semibold">Replay of a real run recorded on {recorded}</span>
      <span className="text-sky-300/80">Not live: the events, numbers and diff are exactly what that run produced.</span>
      <span className="ml-auto flex items-center gap-1" aria-label="Replay speed">
        {SPEEDS.map((s) => (
          <button key={s} onClick={() => setParams({ speed: String(s) })} aria-pressed={s === speed}
            className={`rounded px-2 py-0.5 text-xs ${s === speed ? "bg-sky-400 text-ink-950" : "border border-sky-500/40 hover:bg-sky-500/20"}`}>
            {s === 1 ? "real speed" : `${s}×`}
          </button>
        ))}
      </span>
    </div>
  );
  return <RunView state={state} result={state.finished ? info?.result ?? null : null}
    title={info ? `${info.package}${info.target}` : ""} runId={id} banner={banner} />;
}

export function ReplayList({ intro }: { intro?: React.ReactNode }) {
  const [list, setList] = useState<Replay[] | null>(null);
  useEffect(() => { api.replays().then(setList).catch(() => setList([])); }, []);
  if (!list || list.length === 0) return null;
  return (
    <Card title="Watch a recorded run" right={<span className="text-xs text-ink-400">real runs, replayed in the same UI</span>}>
      {intro}
      <ul className="divide-y divide-ink-700">
        {list.map((r) => (
          <li key={r.id}>
            <Link to={`/replay/${r.id}`} className="flex flex-wrap items-center gap-3 py-2.5 text-sm hover:text-accent">
              <StatusPill status={r.status} />
              <span className="font-medium">{r.title}</span>
              <span className="ml-auto text-xs tabular-nums text-ink-400">
                {r.tests ? `${r.tests.passed} tests passing · ` : ""}{r.coverage != null ? `${r.coverage}% coverage · ` : ""}
                {money(r.cost_usd, 3)} · {r.duration_s != null ? `${Math.round(r.duration_s / 60)} min` : ""}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </Card>
  );
}
