import { useEffect, useState } from "react";
import { api, type RunRow } from "../api";
import { Card, Empty, ErrorBox } from "../components/ui";
import { RunLine } from "./NewMigration";

export default function Runs() {
  const [runs, setRuns] = useState<RunRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api.runs().then(setRuns).catch((e) => setError(e.message)); }, []);
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Runs</h1>
      {error && <ErrorBox>{error}</ErrorBox>}
      {runs && runs.length === 0 && <Empty>No runs yet. Start one from New migration.</Empty>}
      {runs && runs.length > 0 && <Card><ul className="divide-y divide-ink-700">{runs.map((r) => <RunLine key={r.id} r={r} />)}</ul></Card>}
    </div>
  );
}
