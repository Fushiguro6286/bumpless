import { useState } from "react";
import { api, money, type CommentReply } from "../api";
import { Card, ErrorBox } from "./ui";

const EXAMPLES = [
  "@bumpless explain the change in app/models.py",
  "@bumpless revert the change to app/storage.py",
  '@bumpless use model_dump(mode="json") in app/service.py instead',
];

const ROLES: [string, string][] = [
  ["COLLABORATOR", "Collaborator"], ["OWNER", "Owner"], ["CONTRIBUTOR", "Outside contributor (ignored)"],
];

/** Simulates a reviewer comment on the PR: same flow and permission check as the GitHub Action. */
export default function Conversation({ runId, files }: { runId: string; files: string[] }) {
  const [body, setBody] = useState(files[0] ? `@bumpless explain the change in ${files[0]}` : EXAMPLES[0]);
  const [role, setRole] = useState("COLLABORATOR");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [thread, setThread] = useState<{ body: string; role: string; reply: CommentReply }[]>([]);

  const send = async () => {
    setBusy(true); setError(null);
    try {
      const reply = await api.comment(runId, body, role);
      setThread((t) => [...t, { body, role, reply }]);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  return (
    <Card title="PR conversation" right={<span className="text-xs text-ink-400">simulates a review comment; on GitHub the Action does the same</span>}>
      <ol className="space-y-4">
        {thread.map((m, i) => (
          <li key={i} className="space-y-2">
            <div className="rounded-lg border border-ink-700 bg-ink-900 px-3 py-2 text-sm">
              <span className="text-xs text-ink-400">{ROLES.find(([v]) => v === m.role)?.[1]} commented</span>
              <p className="mt-1 font-mono">{m.body}</p>
            </div>
            <div className="rounded-lg border border-accent/40 bg-accent-dim/20 px-3 py-2 text-sm">
              <span className="text-xs text-accent">bumpless replied{m.reply.intent ? ` · intent: ${m.reply.intent}` : ""}
                {m.reply.cost_usd != null ? ` · ${money(m.reply.cost_usd)}` : ""}</span>
              <div className="mt-1 whitespace-pre-wrap">{m.reply.reply ?? "(ignored)"}</div>
              {m.reply.diff && (
                <pre className="mt-2 max-h-80 overflow-auto rounded bg-ink-950 p-2 text-xs leading-5">
                  {m.reply.diff.split("\n").map((l, j) => (
                    <div key={j} className={l.startsWith("+") && !l.startsWith("+++") ? "text-emerald-300" : l.startsWith("-") && !l.startsWith("---") ? "text-rose-300" : "text-ink-300"}>{l || " "}</div>
                  ))}
                </pre>
              )}
            </div>
          </li>
        ))}
      </ol>
      <div className="mt-4 space-y-3">
        <label htmlFor="comment" className="text-xs font-medium text-ink-400">Comment</label>
        <textarea id="comment" value={body} onChange={(e) => setBody(e.target.value)} rows={2}
          className="w-full rounded-lg border border-ink-700 bg-ink-900 px-3 py-2 font-mono text-sm" />
        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <button key={ex} onClick={() => setBody(ex)} className="rounded border border-ink-600 px-2 py-1 text-xs text-ink-300 hover:border-accent">{ex}</button>
          ))}
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-xs text-ink-400">
            Commenter's role
            <select value={role} onChange={(e) => setRole(e.target.value)} className="rounded-md border border-ink-600 bg-ink-850 px-2 py-1.5 text-sm text-ink-100">
              {ROLES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <button onClick={send} disabled={busy || !body.trim()}
            className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-ink-950 hover:brightness-110 disabled:opacity-50">
            {busy ? "Working… (tests re-run, ~1–2 min)" : "Comment"}
          </button>
        </div>
        {error && <ErrorBox>{error}</ErrorBox>}
      </div>
    </Card>
  );
}
