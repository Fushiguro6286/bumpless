import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, money, type Status } from "../api";
import { Card, ErrorBox } from "../components/ui";

function Dot({ ok }: { ok: boolean }) {
  return <span aria-hidden className={`inline-block h-2.5 w-2.5 rounded-full ${ok ? "bg-emerald-400" : "bg-rose-400"}`} />;
}

function Row({ ok, label, detail }: { ok: boolean; label: string; detail?: string | null }) {
  return (
    <li className="flex flex-wrap items-center gap-3 py-2.5 text-sm">
      <Dot ok={ok} />
      <span className="font-medium">{label}</span>
      <span className="sr-only">{ok ? "working" : "unavailable"}</span>
      {detail && <span className="text-xs text-ink-400">{detail}</span>}
    </li>
  );
}

export default function StatusPage() {
  const [s, setS] = useState<Status | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api.status().then(setS).catch((e) => setError(e.message)); }, []);
  return (
    <div className="space-y-6">
      <div className="max-w-3xl">
        <h1 className="text-2xl font-semibold tracking-tight">Status</h1>
        <p className="mt-2 text-sm text-ink-300">What works on this server right now. Recorded runs always work, even with no credits.</p>
      </div>
      {error && <ErrorBox>Could not reach the server: {error}</ErrorBox>}
      {!s && !error && <p className="text-sm text-ink-400">Checking…</p>}
      {s && (
        <>
          <Card title="Live runs">
            <Row ok={s.live.available} label={s.live.available ? "Live runs available" : "Live runs paused"} detail={s.live.reason} />
            {!s.live.available && s.replays > 0 && (
              <p className="mt-2 text-sm text-ink-300">You can still <Link to="/" className="text-accent hover:underline">watch one of {s.replays} recorded real runs</Link>.</p>
            )}
            {s.password_required && <p className="mt-2 text-xs text-ink-400">Live runs on this demo need a password.</p>}
          </Card>
          <div className="grid gap-6 md:grid-cols-2">
            <Card title="NVIDIA Nemotron on Nebius Token Factory">
              <ul className="divide-y divide-ink-700">
                {Object.entries(s.token_factory.models).map(([tier, m]) => (
                  <Row key={tier} ok={m.ok} label={`${tier[0].toUpperCase()}${tier.slice(1)}`} detail={m.model} />
                ))}
              </ul>
              {s.token_factory.error && <p className="mt-2 text-xs text-rose-300">{s.token_factory.error}</p>}
            </Card>
            <Card title="Tavily">
              <ul><Row ok={s.tavily.ok} label={s.tavily.ok ? "Search API reachable" : "Search API unavailable"} detail={s.tavily.error} /></ul>
            </Card>
          </div>
          <Card title="Demo budget (today, UTC)">
            <div className="text-sm">
              <p><span className="text-2xl font-semibold tabular-nums">{money(s.budget.remaining_usd, 2)}</span> left of {money(s.budget.daily_usd, 2)}</p>
              <div className="mt-2 h-2 w-full overflow-hidden rounded bg-ink-700" role="progressbar" aria-label="Budget used"
                aria-valuemin={0} aria-valuemax={s.budget.daily_usd} aria-valuenow={s.budget.spent_today_usd}>
                <div className="h-full bg-accent" style={{ width: `${Math.min(100, (100 * s.budget.spent_today_usd) / (s.budget.daily_usd || 1))}%` }} />
              </div>
              <p className="mt-3 text-ink-300">
                Last successful run: {s.last_successful_run
                  ? <Link to={`/runs/${s.last_successful_run.id}`} className="text-accent hover:underline">{s.last_successful_run.package} · {new Date(s.last_successful_run.created_at * 1000).toLocaleString()}</Link>
                  : "none yet"}
              </p>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
