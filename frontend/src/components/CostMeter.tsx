import type { InvestigationResponse } from "@/lib/api";

export function CostMeter({ investigation }: { investigation: InvestigationResponse }) {
  return (
    <section
      aria-label="Cost"
      className="space-y-2 rounded border border-neutral-200 p-4 dark:border-neutral-800"
    >
      <div className="flex items-baseline justify-between">
        <h3 className="text-xs font-semibold uppercase text-neutral-500">
          Cost for this investigation
        </h3>
        <span className="font-mono text-sm">${investigation.total_cost_usd.toFixed(4)}</span>
      </div>
      {investigation.costs.length === 0 ? (
        <p className="text-xs text-neutral-500">
          No LLM cost recorded for this run — see docs/evidence/cost-and-latency.md for why a
          demo run can legitimately show $0.
        </p>
      ) : (
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-neutral-500">
              <th className="font-normal">Node</th>
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
    </section>
  );
}
