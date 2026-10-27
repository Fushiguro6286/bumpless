import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, money, type Fixture, type RadarRow } from "../api";
import { Card, Empty, ErrorBox } from "../components/ui";

const RISK: Record<string, string> = {
  low: "bg-emerald-500/15 text-emerald-300", medium: "bg-amber-500/15 text-amber-300", high: "bg-rose-500/15 text-rose-300",
};

export default function Radar() {
  const nav = useNavigate();
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [picked, setPicked] = useState("support_bot");
  const [rows, setRows] = useState<RadarRow[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { api.fixtures().then(setFixtures).catch((e) => setError(e.message)); }, []);

  const scan = async () => {
    setBusy(true); setError(null); setRows(null);
    try { setRows((await api.radar(picked)).rows); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };
  const fix = async (r: RadarRow) => {
    setError(null);
    try {
      const { run_id } = await api.start({ fixture: picked, package: r.package, target: r.target, routing: "tiered" });
      nav(`/runs/${run_id}`);
    } catch (e) { setError((e as Error).message); }
  };

  return (
    <div className="space-y-6">
      <div className="max-w-3xl">
        <h1 className="text-2xl font-semibold tracking-tight">Upgrade Radar</h1>
        <p className="mt-2 text-sm text-ink-300">
          Finds pinned dependencies a major version behind, counts how much the code uses them, checks the recipe registry,
          and asks Nemotron Super for a risk estimate. Radar only reads files; it never runs the repository's code.
        </p>
      </div>
      <Card>
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-ink-300">Repository (bundled fixture)</span>
            <select value={picked} onChange={(e) => setPicked(e.target.value)}
              className="rounded-md border border-ink-600 bg-ink-850 px-3 py-2 text-ink-100">
              {fixtures.map((f) => <option key={f.id} value={f.id}>{f.title}</option>)}
            </select>
          </label>
          <button onClick={scan} disabled={busy}
            className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-ink-950 hover:brightness-110 disabled:opacity-50">
            {busy ? "Scanning…" : "Scan"}
          </button>
          <span className="text-xs text-ink-400">For your own repos: <code>bumpless radar &lt;repo&gt;</code></span>
        </div>
      </Card>
      {error && <ErrorBox>{error}</ErrorBox>}
      {rows && rows.length === 0 && <Empty>No pinned dependency is a major version behind.</Empty>}
      {rows && rows.length > 0 && (
        <Card title="Upgrade backlog" right={<span className="text-xs text-ink-400">sorted by value: recipe available, then usage</span>}>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">Dependencies a major version behind</caption>
              <thead className="text-xs uppercase tracking-wide text-ink-400">
                <tr>
                  <th scope="col" className="py-2 pr-3">Package</th><th scope="col" className="pr-3">Pinned → latest</th>
                  <th scope="col" className="pr-3">Usage</th><th scope="col" className="pr-3">Recipe</th>
                  <th scope="col" className="pr-3">Risk</th><th scope="col" className="pr-3">Est. cost</th>
                  <th scope="col"><span className="sr-only">Action</span></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.package} className="border-t border-ink-700 align-top">
                    <td className="py-3 pr-3 font-mono text-ink-100">{r.package}</td>
                    <td className="py-3 pr-3 font-mono text-xs">{r.spec} → {r.latest}</td>
                    <td className="py-3 pr-3">{r.files} files · {r.references} refs</td>
                    <td className="py-3 pr-3">{r.recipe ? <span className="text-accent">v{r.recipe.version} · {r.recipe.verified} verified rules</span> : <span className="text-ink-400">none yet</span>}</td>
                    <td className="py-3 pr-3 max-w-xs">
                      <span className={`rounded px-2 py-0.5 text-xs font-semibold ${RISK[r.risk] ?? "bg-ink-700 text-ink-300"}`}>{r.risk}</span>
                      <p className="mt-1 text-xs text-ink-300">{r.risk_reason}</p>
                    </td>
                    <td className="py-3 pr-3">
                      {r.estimate.usd != null ? `~${money(r.estimate.usd, 2)}` : "—"}
                      <p className="text-xs text-ink-400">estimate · {r.estimate.basis}</p>
                    </td>
                    <td className="py-3">
                      <button onClick={() => fix(r)} aria-label={`Fix ${r.package}: migrate to ${r.target}`}
                        className="rounded-md border border-accent px-3 py-1.5 text-xs font-semibold text-accent hover:bg-accent-dim">
                        Fix
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
