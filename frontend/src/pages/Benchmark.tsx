import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, money, type BenchResult } from "../api";
import { Card, Empty, ErrorBox, Stat, StatusPill } from "../components/ui";

const pct = (v: number | null | undefined) => (v == null ? "—" : `${Math.round(v * 100)}%`);

function latestByRouting(results: BenchResult[]): Record<string, BenchResult> {
  const out: Record<string, BenchResult> = {};
  for (const r of results) if (!out[r.routing]) out[r.routing] = r; // results are newest first
  return out;
}

function Comparison({ latest }: { latest: Record<string, BenchResult> }) {
  const modes = ["tiered", "all-ultra"].filter((m) => latest[m]);
  if (modes.length < 2) {
    return <Empty>Run the benchmark in both routing modes to compare them (<code>bumpless bench --routing all-ultra</code>).</Empty>;
  }
  const data = modes.map((m) => ({
    mode: m, success: Math.round((latest[m].summary.success_rate ?? 0) * 100),
    cost: latest[m].summary.total_cost_usd, median: latest[m].summary.median_cost_usd ?? 0,
  }));
  const chart = (key: "success" | "cost", label: string, fmt: (v: number) => string) => (
    <div>
      <p className="mb-2 text-xs uppercase tracking-wide text-ink-400">{label}</p>
      <div className="h-40" role="img" aria-label={`${label}: ${data.map((d) => `${d.mode} ${fmt(d[key])}`).join(", ")}`}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }}>
            <XAxis type="number" tickFormatter={(v) => fmt(Number(v))} stroke="#7d8a9b" fontSize={11} />
            <YAxis type="category" dataKey="mode" stroke="#7d8a9b" fontSize={12} width={64} />
            <Tooltip formatter={(v) => fmt(Number(v))} contentStyle={{ background: "#10151c", border: "1px solid #1f2732", borderRadius: 8 }} cursor={{ fill: "#151b24" }} />
            <Bar dataKey={key} fill="#34d399" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
  const t = latest["tiered"].summary, u = latest["all-ultra"].summary;
  const saving = u.total_cost_usd ? 1 - t.total_cost_usd / u.total_cost_usd : null;
  return (
    <div className="space-y-4">
      <div className="grid gap-6 md:grid-cols-2">
        {chart("success", "Success rate (green)", (v) => `${v}%`)}
        {chart("cost", "Total cost", (v) => money(v, 3))}
      </div>
      {saving != null && (
        <p className="text-sm text-ink-300">
          Tiered routing cost <span className="font-semibold text-accent">{Math.round(saving * 100)}% less</span> than all-Ultra
          on the same repos ({money(t.total_cost_usd, 3)} vs {money(u.total_cost_usd, 3)}), with {t.green}/{t.repos} vs {u.green}/{u.repos} green.
        </p>
      )}
    </div>
  );
}

function ResultCard({ r }: { r: BenchResult }) {
  const s = r.summary;
  const first = r.runs.filter((x) => !x.recipe_reused), reused = r.runs.filter((x) => x.recipe_reused);
  const avg = (xs: typeof r.runs) => (xs.length ? xs.reduce((a, x) => a + x.cost_usd, 0) / xs.length : null);
  return (
    <Card title={<span className="font-mono">{r.bench_id}</span>}
      right={<span className="text-xs text-ink-400">routing: {r.routing} · {new Date(r.created_at * 1000).toLocaleString()}</span>}>
      <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <Stat label="Green" accent value={`${s.green}/${s.repos}`} sub={`${s.partial} partial · ${s.failed} failed`} />
        <Stat label="Tests fixed" value={`${s.tests_fixed}/${s.tests_failing_before_fix}`} sub="failing after the bump" />
        <Stat label="Coverage (median)" value={s.median_coverage_percent != null ? `${s.median_coverage_percent}%` : "—"} sub="verified change coverage" />
        <Stat label="Behavior kept (median)" value={pct(s.median_characterization_pass_rate)} sub="characterization tests" />
        <Stat label="Cost" value={money(s.median_cost_usd)} sub={`median · total ${money(s.total_cost_usd, 3)}`} />
        <Stat label="Time (median)" value={s.median_duration_s != null ? `${Math.round(s.median_duration_s)}s` : "—"} sub={`${s.escalations} escalations`} />
      </div>
      {first.length > 0 && reused.length > 0 && (
        <p className="mt-3 text-sm text-ink-300">
          Recipe reuse: first runs averaged {money(avg(first))}, runs that reused a recipe averaged {money(avg(reused))}.
        </p>
      )}
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">Per-repository results for {r.bench_id}</caption>
          <thead className="text-xs uppercase tracking-wide text-ink-400">
            <tr>
              <th scope="col" className="py-2 pr-3">Repo</th><th scope="col" className="pr-3">Status</th>
              <th scope="col" className="pr-3">Tests fixed</th><th scope="col" className="pr-3">Behavior kept</th>
              <th scope="col" className="pr-3">Coverage</th><th scope="col" className="pr-3">Cost</th>
              <th scope="col" className="pr-3">Time</th><th scope="col" className="pr-3">Recipe</th>
            </tr>
          </thead>
          <tbody>
            {r.runs.map((x) => (
              <tr key={x.run_id} className="border-t border-ink-700">
                <td className="py-2 pr-3">
                  <Link className="font-mono text-ink-100 hover:text-accent" to={`/runs/${x.run_id}`}>{x.name}</Link>
                  <span className="ml-2 text-xs text-ink-400">{x.kind} · {x.package} {x.old_version} → {x.new_version}</span>
                </td>
                <td className="pr-3"><StatusPill status={x.status} /></td>
                <td className="pr-3">{x.tests_fixed}/{x.tests_failing_before_fix}</td>
                <td className="pr-3">{pct(x.characterization_pass_rate)}</td>
                <td className="pr-3">{x.coverage_percent != null ? `${x.coverage_percent}%` : "—"}</td>
                <td className="pr-3">{money(x.cost_usd)}</td>
                <td className="pr-3">{Math.round(x.duration_s)}s</td>
                <td className="pr-3 text-xs text-ink-300">{x.recipe_reused ? "reused" : "first run"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

export default function Benchmark() {
  const [results, setResults] = useState<BenchResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api.bench().then(setResults).catch((e) => setError(e.message)); }, []);
  const latest = results ? latestByRouting(results) : {};
  return (
    <div className="space-y-6">
      <div className="max-w-3xl">
        <h1 className="text-2xl font-semibold tracking-tight">Benchmark</h1>
        <p className="mt-2 text-sm text-ink-300">
          Every number here comes from a stored real run (<code className="text-ink-100">benchmarks/results/</code>). Each repo is
          migrated end to end in the sandbox; click a repo to open its full run.
        </p>
      </div>
      {error && <ErrorBox>{error}</ErrorBox>}
      {results && results.length === 0 && <Empty>No benchmark results yet. Run <code>bumpless bench benchmarks/repos.yaml</code>.</Empty>}
      {results && results.length > 0 && (
        <>
          <Card title="Tiered vs all-Ultra routing"><Comparison latest={latest} /></Card>
          {Object.values(latest).map((r) => <ResultCard key={r.bench_id} r={r} />)}
        </>
      )}
    </div>
  );
}
