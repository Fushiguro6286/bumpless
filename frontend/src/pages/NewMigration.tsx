import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, type Fixture, type RunRow, type Status } from "../api";
import { Card, ErrorBox, StatusPill } from "../components/ui";
import { ReplayList } from "./Replay";

export default function NewMigration() {
  const nav = useNavigate();
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [runs, setRuns] = useState<RunRow[]>([]);
  const [picked, setPicked] = useState<string>("");
  const [pkg, setPkg] = useState("");
  const [target, setTarget] = useState("");
  const [routing, setRouting] = useState("tiered");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<Status | null>(null);
  const [password, setPassword] = useState("");

  useEffect(() => {
    api.status().then(setStatus).catch(() => {});
    api.fixtures().then((f) => { setFixtures(f); if (f[0]) choose(f[0]); }).catch((e) => setError(e.message));
    api.runs().then(setRuns).catch(() => {});
  }, []);

  function choose(f: Fixture) { setPicked(f.id); setPkg(f.package); setTarget(f.target); }

  async function start() {
    setBusy(true); setError(null);
    try {
      const { run_id } = await api.start({ fixture: picked, package: pkg, target, routing }, password);
      nav(`/runs/${run_id}`);
    } catch (e) { setError((e as Error).message); setBusy(false); }
  }

  return (
    <div className="space-y-10">
      <section className="max-w-3xl">
        <p className="text-sm font-medium text-accent">Dependency upgrades, finished</p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight sm:text-5xl">Dependabot bumps the version.<br />Bumpless makes it pass.</h1>
        <p className="mt-4 text-ink-300">
          Pick a repository and a target version. Bumpless researches the breaking changes in the live docs with Tavily,
          verifies every rule against its source, records today's behavior, migrates the code with NVIDIA Nemotron on
          Nebius Token Factory, and hands you a PR where every change is cited and tested.
        </p>
      </section>

      {status && !status.live.available && (
        <div role="status" className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
          {status.live.reason} Meanwhile, watch a recorded real run below: same UI, same numbers, clearly labelled as a replay.
        </div>
      )}
      {status && !status.live.available && <ReplayList />}

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Card title="1 · Repository">
          <fieldset>
            <legend className="sr-only">Choose a fixture repository</legend>
            <div className="grid gap-3 sm:grid-cols-2">
              {fixtures.map((f) => (
                <label key={f.id}
                  className={`cursor-pointer rounded-lg border p-3 transition-colors focus-within:ring-2 focus-within:ring-accent ${picked === f.id ? "border-accent bg-accent-dim/40" : "border-ink-700 hover:border-ink-600"}`}>
                  <input type="radio" name="fixture" value={f.id} checked={picked === f.id} onChange={() => choose(f)} className="sr-only" />
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{f.title}</span>
                    <code className="rounded bg-ink-700 px-1.5 py-0.5 text-[11px] text-ink-300">{f.package}{f.target}</code>
                  </div>
                  <p className="mt-1 text-xs text-ink-400">{f.description}</p>
                </label>
              ))}
            </div>
          </fieldset>
          <div className="mt-4">
            <label htmlFor="repo" className="text-xs font-medium text-ink-400">Your own GitHub repository</label>
            <input id="repo" disabled placeholder="https://github.com/you/your-repo"
              className="mt-1 w-full cursor-not-allowed rounded-lg border border-ink-700 bg-ink-900 px-3 py-2 text-sm text-ink-400" />
            <p className="mt-1 text-xs text-ink-400">
              The hosted demo only runs bundled fixtures (it never executes untrusted code). Run any repo with
              <code className="mx-1 rounded bg-ink-700 px-1">bumpless run</code> or the GitHub Action.
            </p>
          </div>
        </Card>

        <Card title="2 · Upgrade">
          <div className="space-y-4">
            <div>
              <label htmlFor="pkg" className="text-xs font-medium text-ink-400">Package</label>
              <input id="pkg" value={pkg} onChange={(e) => setPkg(e.target.value)}
                className="mt-1 w-full rounded-lg border border-ink-700 bg-ink-900 px-3 py-2 font-mono text-sm" />
            </div>
            <div>
              <label htmlFor="target" className="text-xs font-medium text-ink-400">Target version</label>
              <input id="target" value={target} onChange={(e) => setTarget(e.target.value)}
                className="mt-1 w-full rounded-lg border border-ink-700 bg-ink-900 px-3 py-2 font-mono text-sm" />
            </div>
            <fieldset>
              <legend className="text-xs font-medium text-ink-400">Model routing</legend>
              <div className="mt-1 grid grid-cols-2 gap-2">
                {[["tiered", "Tiered", "Nano → Super → Ultra by task"], ["all-ultra", "All Ultra", "every call on Ultra"]].map(([v, l, d]) => (
                  <label key={v} className={`cursor-pointer rounded-lg border px-3 py-2 text-sm focus-within:ring-2 focus-within:ring-accent ${routing === v ? "border-accent" : "border-ink-700"}`}>
                    <input type="radio" name="routing" value={v} checked={routing === v} onChange={() => setRouting(v)} className="sr-only" />
                    <div className="font-medium">{l}</div><div className="text-xs text-ink-400">{d}</div>
                  </label>
                ))}
              </div>
            </fieldset>
            {status?.password_required && (
              <div>
                <label htmlFor="pw" className="text-xs font-medium text-ink-400">Demo password</label>
                <input id="pw" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-ink-700 bg-ink-900 px-3 py-2 text-sm" />
              </div>
            )}
            {error && <ErrorBox>{error}</ErrorBox>}
            <button onClick={start} disabled={busy || !picked || !pkg || !target || status?.live.available === false}
              className="w-full rounded-lg bg-accent px-4 py-2.5 font-semibold text-ink-950 transition hover:brightness-110 disabled:opacity-50">
              {busy ? "Starting…" : "Run migration"}
            </button>
            <p className="text-xs text-ink-400">A live run takes a few minutes and costs a few cents of Token Factory credit.</p>
          </div>
        </Card>
      </div>

      {(!status || status.live.available) && <ReplayList />}

      <Card title="Recent runs" right={<Link to="/runs" className="text-xs text-ink-300 hover:text-accent">All runs →</Link>}>
        {runs.length === 0 ? <p className="text-sm text-ink-400">No runs yet.</p> : (
          <ul className="divide-y divide-ink-700">
            {runs.slice(0, 6).map((r) => <RunLine key={r.id} r={r} />)}
          </ul>
        )}
      </Card>
    </div>
  );
}

export function RunLine({ r }: { r: RunRow }) {
  return (
    <li>
      <Link to={`/runs/${r.id}`} className="flex flex-wrap items-center gap-3 py-2.5 text-sm hover:text-accent">
        <StatusPill status={r.status} />
        <span className="font-medium">{r.repo}</span>
        <code className="text-xs text-ink-400">{r.package}{r.target}</code>
        <span className="text-xs text-ink-400">{r.routing}</span>
        <span className="ml-auto text-xs tabular-nums text-ink-400">{new Date(r.created_at * 1000).toLocaleString()}</span>
      </Link>
    </li>
  );
}
