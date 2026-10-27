import { useMemo, useState } from "react";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, money, type CovHunk, type RunResult, type Tier } from "../api";
import { Card, ConfidenceBadge, SourceChip, Stat, StatusPill, TierBadge, TIER_COLOR, TIER_LABEL, VerifiedBadge } from "../components/ui";

export default function Result({ r, runId, children }: { r: RunResult; runId: string; children?: React.ReactNode }) {
  const t = r.tests;
  const charAfter = (t.after?.failing ?? []).filter((x) => x.startsWith("tests._bumpless")).length;
  const repoAfter = t.after ? { passed: t.after.passed - (r.characterization?.observations ?? 0) + charAfter, failed: t.after.failed - charAfter } : null;
  const cov = r.coverage;
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-ink-700 bg-ink-850 px-4 py-3">
          <div className="text-xs font-medium uppercase tracking-wide text-ink-400">Result</div>
          <div className="mt-2 flex items-center gap-2"><StatusPill status={r.status} /><span className="text-sm text-ink-300">{r.package} {r.old_version} → {r.new_version}</span></div>
          <div className="mt-2 text-xs text-ink-400">{Math.round(r.duration_s)}s · {r.executor} sandbox</div>
        </div>
        <Stat label="Verified change coverage" accent
          value={cov?.measured && cov.percent != null ? `${cov.percent}%` : "—"}
          sub={cov?.measured ? `${cov.executed_changed_lines} of ${cov.executable_changed_lines} changed lines executed by tests` : "not measured"} />
        <Stat label="Behavior preserved" value={r.characterization?.observations ? `${r.characterization.observations - charAfter}/${r.characterization.observations}` : "—"}
          sub="characterization checks recorded on the old version" />
        <Stat label="Total cost" value={money(r.cost.total_usd)} sub={`${r.cost.llm_calls} Nemotron calls · ${r.tavily.calls} Tavily calls`} />
      </div>

      <Card title="Tests: red → green">
        <div className="grid gap-3 sm:grid-cols-3">
          <TestBox label={`Old version (${r.old_version})`} t={t.old} />
          <TestBox label={`New version, before fix (${r.new_version})`} t={t.new_before} red />
          <TestBox label="After Bumpless" t={repoAfter ? { ...t.after!, ...repoAfter } : undefined} />
        </div>
        {r.characterization?.observations > 0 && (
          <p className="mt-3 text-xs text-ink-400">
            Plus {r.characterization.observations} generated characterization tests in <code>tests/_bumpless/</code>:{" "}
            {r.characterization.new_before?.failed ?? 0} differed before the fix, {charAfter} differ after.
          </p>
        )}
      </Card>

      <Actions r={r} runId={runId} />
      {children}
      <DiffView hunks={cov?.hunks ?? []} rules={r.rulebook?.rules ?? []} />
      <div className="grid gap-6 lg:grid-cols-2">
        <CostChart r={r} />
        <ReviewCard r={r} />
      </div>
      <TavilyPanel r={r} />
    </div>
  );
}

function TestBox({ label, t, red }: { label: string; t?: { passed: number; failed: number }; red?: boolean }) {
  return (
    <div className={`rounded-lg border px-3 py-3 ${red && t && t.failed ? "border-rose-500/30 bg-rose-500/5" : "border-ink-700 bg-ink-900"}`}>
      <div className="text-xs text-ink-400">{label}</div>
      {t ? (
        <div className="mt-1 text-lg font-semibold tabular-nums">
          <span className="text-emerald-300">{t.passed} passed</span>
          <span className={`ml-3 ${t.failed ? "text-rose-300" : "text-ink-400"}`}>{t.failed} failed</span>
        </div>
      ) : <div className="mt-1 text-ink-400">—</div>}
    </div>
  );
}

function Actions({ r, runId }: { r: RunResult; runId: string }) {
  const [copied, setCopied] = useState<string | null>(null);
  async function share() {
    const url = window.location.origin + `/runs/${runId}`;
    const md = `**Bumpless** migrated \`${r.package}\` ${r.old_version} → ${r.new_version}: **${r.status}**, ` +
      `tests ${r.tests.new_before?.passed ?? 0}→${r.tests.after?.passed ?? 0} passing, verified change coverage ` +
      `${r.coverage?.percent ?? "n/a"}%, cost ${money(r.cost.total_usd)}. ${url}`;
    await navigator.clipboard.writeText(md);
    setCopied("Permalink + summary copied");
    setTimeout(() => setCopied(null), 2500);
  }
  async function downloadReport() {
    const text = await api.report(runId);
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type: "text/markdown" }));
    a.download = `bumpless-${runId}-report.md`;
    a.click();
  }
  return (
    <div className="flex flex-wrap items-center gap-3">
      {r.output?.pr_url && <a href={r.output.pr_url} target="_blank" rel="noreferrer" className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-ink-950 hover:brightness-110">Open pull request</a>}
      <a href={`/api/runs/${runId}/patch`} download={`bumpless-${runId}.patch`} className="rounded-lg border border-ink-600 px-4 py-2 text-sm hover:border-accent">Download patch</a>
      <button onClick={downloadReport} className="rounded-lg border border-ink-600 px-4 py-2 text-sm hover:border-accent">PR report (Markdown)</button>
      <button onClick={share} className="rounded-lg border border-ink-600 px-4 py-2 text-sm hover:border-accent">Share</button>
      <span aria-live="polite" className="text-xs text-accent">{copied}</span>
      {!r.output?.pr_url && r.output?.pr_skipped_reason && <span className="text-xs text-ink-400">No PR: {r.output.pr_skipped_reason}</span>}
    </div>
  );
}

function DiffView({ hunks, rules }: { hunks: CovHunk[]; rules: { id: string; title: string }[] }) {
  const [onlyLow, setOnlyLow] = useState(false);
  const titles = useMemo(() => Object.fromEntries(rules.map((x) => [x.id, x.title])), [rules]);
  const shown = onlyLow ? hunks.filter((h) => h.confidence === "Low") : hunks;
  const files = useMemo(() => {
    const m = new Map<string, CovHunk[]>();
    shown.forEach((h) => m.set(h.path, [...(m.get(h.path) ?? []), h]));
    return [...m.entries()];
  }, [shown]);
  const lows = hunks.filter((h) => h.confidence === "Low").length;
  return (
    <Card title={`Changes (${hunks.length} hunks)`} right={
      <label className="flex items-center gap-2 text-xs text-ink-300">
        <input type="checkbox" checked={onlyLow} onChange={(e) => setOnlyLow(e.target.checked)} className="accent-[var(--color-accent)]" />
        Show only Low confidence ({lows})
      </label>}>
      {files.length === 0 ? <p className="text-sm text-ink-400">{onlyLow ? "No Low-confidence changes." : "No code changes."}</p> : (
        <div className="space-y-5">
          {files.map(([path, hs]) => (
            <div key={path}>
              <h3 className="mb-2 font-mono text-sm text-ink-100">{path}</h3>
              <div className="space-y-3">
                {hs.map((h, i) => (
                  <div key={i} className="overflow-hidden rounded-lg border border-ink-700">
                    <div className="flex flex-wrap items-center gap-2 border-b border-ink-700 bg-ink-900 px-3 py-2 text-xs">
                      <span className="font-mono text-ink-400">L{h.start}</span>
                      <ConfidenceBadge level={h.confidence} />
                      {h.rule_id && <span className="text-ink-300"><code className="text-ink-400">{h.rule_id}</code> {titles[h.rule_id] ?? ""}</span>}
                      {h.source_url && <SourceChip url={h.source_url} official />}
                      {h.rule_id && <VerifiedBadge ok={h.verified} />}
                      <span className="ml-auto flex items-center gap-1.5">
                        <TierBadge tier={h.model_tier} />{h.escalated && <span className="text-amber-300">escalated</span>}{h.repaired && <span className="text-violet-300">repair</span>}
                      </span>
                    </div>
                    <div className="grid font-mono text-[12.5px] leading-5 md:grid-cols-2">
                      <pre className="overflow-x-auto bg-rose-500/[0.06] px-3 py-2 text-rose-200/90">{h.removed.length ? h.removed.map((l) => `- ${l}`).join("\n") : " "}</pre>
                      <pre className="overflow-x-auto bg-emerald-500/[0.06] px-3 py-2 text-emerald-200/90 md:border-l md:border-ink-700">{h.added.length ? h.added.map((l) => `+ ${l}`).join("\n") : " "}</pre>
                    </div>
                    {h.confidence !== "High" && <div className="border-t border-ink-700 px-3 py-1.5 text-xs text-ink-400">{h.reasons.join(" · ")}</div>}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function CostChart({ r }: { r: RunResult }) {
  const tiers: Tier[] = ["nano", "super", "ultra"];
  const data = tiers.map((t) => ({ tier: TIER_LABEL[t], usd: r.cost.by_tier[t], key: t }));
  return (
    <Card title="Cost by model tier" right={<span className="text-xs text-ink-400">{r.routing} routing</span>}>
      <div className="h-44" role="img" aria-label={`Cost: ${data.map((d) => `${d.tier} ${money(d.usd)}`).join(", ")}`}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }}>
            <XAxis type="number" tickFormatter={(v) => `$${v.toFixed(3)}`} stroke="#7d8a9b" fontSize={11} />
            <YAxis type="category" dataKey="tier" stroke="#7d8a9b" fontSize={12} width={48} />
            <Tooltip formatter={(v) => money(Number(v))} contentStyle={{ background: "#10151c", border: "1px solid #1f2732", borderRadius: 8 }} cursor={{ fill: "#151b24" }} />
            <Bar dataKey="usd" radius={[0, 4, 4, 0]}>{data.map((d) => <Cell key={d.key} fill={TIER_COLOR[d.key]} />)}</Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      {r.escalations.length > 0 && <p className="mt-2 text-xs text-amber-300">{r.escalations.length} escalation(s): {r.escalations.map((e) => `${e.path} → ${e.tier}`).join(", ")}</p>}
    </Card>
  );
}

function ReviewCard({ r }: { r: RunResult }) {
  return (
    <Card title={`Needs human review (${r.manual_review.length})`}>
      {r.review && <p className="mb-3 text-sm text-ink-300">Guardrails: {r.review.violations.length} violation(s). Ultra review: {r.review.approve ? "approved" : "flagged changes"}. {r.review.summary}</p>}
      {r.manual_review.length === 0 ? <p className="text-sm text-ink-400">Nothing flagged.</p> : (
        <ul className="max-h-72 space-y-2 overflow-y-auto pr-1 text-sm">
          {r.manual_review.map((m, i) => <li key={i} className="rounded-md bg-ink-900 px-3 py-2 text-ink-300">{m}</li>)}
        </ul>
      )}
    </Card>
  );
}

function TavilyPanel({ r }: { r: RunResult }) {
  const rb = r.rulebook;
  return (
    <Card title="Tavily usage" right={<span className="text-xs text-ink-400">{Object.entries(r.tavily.by_kind).map(([k, v]) => `${k} ${v}`).join(" · ")}</span>}>
      <p className="mb-3 text-sm text-ink-300">
        {r.recipe_reused ? `Recipe reused (v${rb?.recipe_version}); research skipped. ` : `Rulebook built from ${rb?.official_pages ?? 0} official pages. `}
        {rb && `${rb.rules.filter((x) => x.verified).length}/${rb.rules.length} rules verified against their sources.`}
      </p>
      {r.tavily.log.length === 0 ? <p className="text-sm text-ink-400">No Tavily calls in this run.</p> : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-ink-400"><tr><th className="py-2 pr-3 font-medium">Call</th><th className="py-2 pr-3 font-medium">Query / URL</th><th className="py-2 pr-3 font-medium">Results</th><th className="py-2 font-medium">Rules from it</th></tr></thead>
            <tbody className="divide-y divide-ink-700">
              {r.tavily.log.map((c, i) => (
                <tr key={i}>
                  <td className="py-2 pr-3"><code className="text-xs">{c.kind}</code>{c.cached && <span className="ml-1 text-[11px] text-ink-400">cached</span>}</td>
                  <td className="max-w-md truncate py-2 pr-3 text-ink-300" title={c.query}>{c.query}</td>
                  <td className="py-2 pr-3 tabular-nums">{c.results}</td>
                  <td className="py-2 text-xs text-ink-300">{c.rules.length ? c.rules.join(", ") : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
