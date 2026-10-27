import type { ReactNode } from "react";
import type { Tier } from "../api";

export const TIER_STYLE: Record<Tier, string> = {
  nano: "bg-sky-500/15 text-sky-300 ring-sky-400/30",
  super: "bg-violet-500/15 text-violet-300 ring-violet-400/30",
  ultra: "bg-amber-500/15 text-amber-300 ring-amber-400/30",
};
export const TIER_COLOR: Record<Tier, string> = { nano: "#38bdf8", super: "#a78bfa", ultra: "#fbbf24" };
export const TIER_LABEL: Record<Tier, string> = { nano: "Nano", super: "Super", ultra: "Ultra" };

export function TierBadge({ tier }: { tier: Tier | null | undefined }) {
  if (!tier) return null;
  return <span className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[11px] font-medium ring-1 ring-inset ${TIER_STYLE[tier]}`}>{TIER_LABEL[tier]}</span>;
}

const CONF: Record<string, string> = {
  High: "bg-emerald-500/15 text-emerald-300 ring-emerald-400/30",
  Medium: "bg-yellow-500/15 text-yellow-200 ring-yellow-400/30",
  Low: "bg-rose-500/15 text-rose-300 ring-rose-400/30",
};

export function ConfidenceBadge({ level }: { level: string }) {
  return <span className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[11px] font-semibold ring-1 ring-inset ${CONF[level]}`}>{level}</span>;
}

export function VerifiedBadge({ ok }: { ok: boolean }) {
  return ok ? (
    <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-300" title="Verified against its source page">
      <svg aria-hidden viewBox="0 0 16 16" className="size-3.5 fill-current"><path d="M6.5 11.2 3.3 8l1.1-1.1 2.1 2.1 5.1-5.1L12.7 5z" /></svg>verified
    </span>
  ) : (
    <span className="text-[11px] font-medium text-rose-300" title="Source page does not support this rule; never applied automatically">unverified</span>
  );
}

const STATUS: Record<string, string> = {
  green: "bg-emerald-500/15 text-emerald-300 ring-emerald-400/40",
  partial: "bg-yellow-500/15 text-yellow-200 ring-yellow-400/40",
  failed: "bg-rose-500/15 text-rose-300 ring-rose-400/40",
  running: "bg-sky-500/15 text-sky-300 ring-sky-400/40",
};

export function StatusPill({ status }: { status: string }) {
  return <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide ring-1 ring-inset ${STATUS[status] ?? STATUS.running}`}>{status}</span>;
}

export function Card({ title, right, children, className = "" }: { title?: ReactNode; right?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-xl border border-ink-700 bg-ink-850 ${className}`}>
      {title && (
        <header className="flex items-center justify-between gap-3 border-b border-ink-700 px-4 py-3">
          <h2 className="text-sm font-semibold text-ink-100">{title}</h2>
          {right}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

export function Stat({ label, value, sub, accent = false }: { label: string; value: ReactNode; sub?: ReactNode; accent?: boolean }) {
  return (
    <div className="rounded-xl border border-ink-700 bg-ink-850 px-4 py-3">
      <div className="text-xs font-medium uppercase tracking-wide text-ink-400">{label}</div>
      <div className={`mt-1 text-2xl font-semibold tabular-nums ${accent ? "text-accent" : "text-ink-100"}`}>{value}</div>
      {sub && <div className="mt-0.5 text-xs text-ink-400">{sub}</div>}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="rounded-xl border border-dashed border-ink-600 px-6 py-10 text-center text-sm text-ink-400">{children}</div>;
}

export function ErrorBox({ children }: { children: ReactNode }) {
  return <div role="alert" className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{children}</div>;
}

export function hostOf(url: string) {
  try { return new URL(url).hostname.replace(/^www\./, ""); } catch { return url; }
}

export function SourceChip({ url, official }: { url: string; official?: boolean }) {
  const path = (() => { try { const u = new URL(url); return u.pathname.replace(/\/$/, "").split("/").slice(-2).join("/"); } catch { return ""; } })();
  return (
    <a href={url} target="_blank" rel="noreferrer"
      className={`inline-flex max-w-full items-center gap-1.5 truncate rounded-full border px-2.5 py-1 text-xs hover:border-accent hover:text-accent ${official ? "border-emerald-500/40 text-emerald-200" : "border-ink-600 text-ink-300"}`}
      title={url}>
      {official && <span className="size-1.5 shrink-0 rounded-full bg-accent" aria-label="official source" />}
      <span className="truncate">{hostOf(url)}{path && <span className="text-ink-400">/{path}</span>}</span>
    </a>
  );
}
