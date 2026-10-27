import { useEffect, useRef } from "react";
import { TierBadge } from "./ui";
import type { Tier } from "../api";

const FLOW: { step: string; what: string; tier?: Tier; tool?: string }[] = [
  { step: "Baseline", what: "Run tests on the old version, then on the new one: the Dependabot red", tool: "Docker sandbox" },
  { step: "Research", what: "Search, map and extract the official migration docs", tool: "Tavily" },
  { step: "Rulebook", what: "Summarize pages, then synthesize rules with sources", tier: "super" },
  { step: "Verify sources", what: "Check every rule against the text of the page it cites", tier: "nano" },
  { step: "Characterize", what: "Record today's behavior as golden tests", tier: "super" },
  { step: "Plan", what: "Order files, map rules to files, flag risk", tier: "ultra" },
  { step: "Edit", what: "Parallel search/replace edits; escalate to Super then Ultra on failure", tier: "nano" },
  { step: "Verify & repair", what: "Sandboxed tests; diagnose failures, look up unknown errors", tier: "ultra" },
  { step: "Coverage", what: "Which changed lines were executed by a test?", tool: "coverage.py" },
  { step: "Review", what: "Code guardrails + a final review pass", tier: "ultra" },
  { step: "PR", what: "Every change cites its source with a confidence level", tool: "GitHub" },
];

export function AboutModal({ onClose }: { onClose: () => void }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    ref.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => { window.removeEventListener("keydown", onKey); prev?.focus(); };
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div ref={ref} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="about-title"
        className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-ink-700 bg-ink-850 p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="about-title" className="text-xl font-semibold">How Bumpless works</h2>
            <p className="mt-1 text-sm text-ink-300">
              Model training data predates new library versions, which is exactly why upgrades break. Bumpless researches
              the live docs, proves every rule against its source, and proves behavior did not change.
            </p>
          </div>
          <button onClick={onClose} className="rounded-md px-2 py-1 text-ink-300 hover:text-ink-100" aria-label="Close">✕</button>
        </div>
        <ol className="mt-5 space-y-2">
          {FLOW.map((f, i) => (
            <li key={f.step} className="flex items-start gap-3 rounded-lg border border-ink-700 bg-ink-900 px-3 py-2">
              <span className="mt-0.5 w-5 shrink-0 text-right text-xs tabular-nums text-ink-400">{i + 1}</span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2 text-sm font-medium">
                  {f.step} {f.tier && <TierBadge tier={f.tier} />}
                  {f.tool && <span className="rounded-md bg-ink-700 px-1.5 py-0.5 text-[11px] text-ink-300">{f.tool}</span>}
                </div>
                <div className="text-xs text-ink-400">{f.what}</div>
              </div>
            </li>
          ))}
        </ol>
        <p className="mt-5 text-xs text-ink-400">
          Routing: Nemotron 3 Nano for cheap high-volume calls, Super for long-context synthesis, Ultra for serious reasoning.
          All inference runs on Nebius Token Factory.
        </p>
      </div>
    </div>
  );
}
