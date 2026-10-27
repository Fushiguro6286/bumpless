import { useState } from "react";
import { Link } from "react-router-dom";

const KEY = "bumpless.tour.done";
const STEPS = [
  { title: "Start a migration", body: "Pick a fixture repo and a target version, then press Run. No live credits? Watch a recorded run below." },
  { title: "Watch it work", body: "The run view shows each step live: Tavily sources and verified rules, the old behavior recorded as tests, Nemotron edits with their tier and cost, and tests going red to green." },
  { title: "Check the evidence", body: "The result shows verified change coverage and, for every change, a confidence, the rule and its source. You can also reply to it like a PR reviewer." },
  { title: "Explore", body: "Radar finds a repo's upgrade backlog. Benchmark compares tiered routing with all-Ultra on every stored run." },
];

function seen(): boolean {
  try { return localStorage.getItem(KEY) === "1"; } catch { return false; }
}

/** First-visit tour. `force` reopens it (from the "Tour" button). */
export default function Tour({ force = false, onClose }: { force?: boolean; onClose?: () => void }) {
  const [open, setOpen] = useState(force || !seen());
  const [i, setI] = useState(0);
  if (!open) return null;
  const close = () => {
    try { localStorage.setItem(KEY, "1"); } catch { /* private mode: show again next time */ }
    setOpen(false); onClose?.();
  };
  const s = STEPS[i];
  return (
    <section aria-labelledby="tour-title" aria-live="polite" className="mb-6 rounded-xl border border-accent/40 bg-ink-850 p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-accent">Quick tour · {i + 1} of {STEPS.length}</p>
          <h2 id="tour-title" className="mt-1 text-lg font-semibold">{s.title}</h2>
          <p className="mt-1 max-w-2xl text-sm text-ink-300">{s.body}</p>
          {i === STEPS.length - 1 && (
            <p className="mt-2 flex gap-3 text-sm">
              <Link to="/radar" onClick={close} className="text-accent underline">Radar</Link>
              <Link to="/benchmark" onClick={close} className="text-accent underline">Benchmark</Link>
            </p>
          )}
        </div>
        <button onClick={close} className="rounded-md px-2 py-1 text-sm text-ink-300 hover:text-ink-100">Skip tour</button>
      </div>
      <div className="mt-4 flex gap-2">
        <button onClick={() => setI(i - 1)} disabled={i === 0}
          className="rounded-md border border-ink-600 px-3 py-1.5 text-sm disabled:opacity-40">Back</button>
        {i < STEPS.length - 1
          ? <button onClick={() => setI(i + 1)} className="rounded-md bg-accent px-3 py-1.5 text-sm font-semibold text-ink-950">Next</button>
          : <button onClick={close} className="rounded-md bg-accent px-3 py-1.5 text-sm font-semibold text-ink-950">Done</button>}
      </div>
    </section>
  );
}
