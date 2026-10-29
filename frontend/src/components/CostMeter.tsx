import { Card, CardTitle } from "@/components/ui/Card";
import type { InvestigationResponse } from "@/lib/api";

export function CostMeter({ investigation }: { investigation: InvestigationResponse }) {
  return (
    <Card aria-label="Cost" className="space-y-3">
      <div className="flex items-baseline justify-between">
        <CardTitle>Cost for this investigation</CardTitle>
        <span className="font-mono text-sm text-slate-900 dark:text-white">
          ${investigation.total_cost_usd.toFixed(4)}
        </span>
      </div>
      {investigation.costs.length === 0 ? (
        <p className="text-xs text-slate-500 dark:text-slate-400">
          No model cost was recorded for this run. Rules, tools and checks cost nothing; only the AI
          steps do.
        </p>
      ) : (
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-slate-500 dark:text-slate-400">
              <th className="font-normal">Step</th>
              <th className="font-normal">Model</th>
              <th className="font-normal">Tokens</th>
              <th className="font-normal">Cost</th>
            </tr>
          </thead>
          <tbody>
            {investigation.costs.map((entry, i) => (
              <tr key={i}>
                <td className="font-mono">{entry.node}</td>
                <td>{entry.model}</td>
                <td>{entry.prompt_tokens + entry.completion_tokens}</td>
                <td>${entry.cost_usd.toFixed(4)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}
