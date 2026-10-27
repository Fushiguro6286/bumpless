import { useEffect, useState } from "react";
import { api, money, type Recipe } from "../api";
import { Card, Empty, ErrorBox, Stat } from "../components/ui";

export default function Recipes() {
  const [recipes, setRecipes] = useState<Recipe[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api.recipes().then(setRecipes).catch((e) => setError(e.message)); }, []);
  return (
    <div className="space-y-6">
      <div className="max-w-3xl">
        <h1 className="text-2xl font-semibold tracking-tight">Migration recipes</h1>
        <p className="mt-2 text-sm text-ink-300">
          Every successful run saves its verified rulebook as a recipe in the public registry
          (<code className="text-ink-100">recipes/&lt;package&gt;/&lt;from&gt;-to-&lt;to&gt;.json</code>). The next repo skips research,
          stale recipes get a Tavily freshness check, and rules learned during repairs are merged back.
        </p>
      </div>
      {error && <ErrorBox>{error}</ErrorBox>}
      {recipes && recipes.length === 0 && <Empty>No recipes yet. They appear after the first successful run.</Empty>}
      {recipes?.map((r) => {
        const saving = r.avg_first_run_cost && r.avg_reused_run_cost ? 1 - r.avg_reused_run_cost / r.avg_first_run_cost : null;
        return (
          <Card key={r.recipe} title={<span className="font-mono">{r.package} {r.from} → {r.to}</span>}
            right={<span className="text-xs text-ink-400">v{r.recipe_version} · checked {r.checked_at.slice(0, 10)}</span>}>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
              <Stat label="Rules" value={r.rules} sub={`${r.verified_rules} verified against sources`} />
              <Stat label="Runs" value={r.runs} sub={r.success_rate != null ? `${Math.round(r.success_rate * 100)}% green` : "—"} />
              <Stat label="First run (avg)" value={money(r.avg_first_run_cost)} sub="research from scratch" />
              <Stat label="Reused (avg)" value={money(r.avg_reused_run_cost)} sub="research skipped" />
              <Stat label="Saving" accent value={saving != null ? `${Math.round(saving * 100)}%` : "—"} sub="reuse vs first run" />
            </div>
            <p className="mt-3 text-xs text-ink-400">File: <code>{r.path}</code></p>
          </Card>
        );
      })}
    </div>
  );
}
