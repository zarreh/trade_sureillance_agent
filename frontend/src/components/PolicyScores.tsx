import type { RlPolicies } from "@/lib/schemas";

const pct = (v: number | null) => (v === null ? "n/a" : `${Math.round(v * 100)}%`);
const score = (v: number | null) => (v === null ? "n/a" : v.toFixed(2));

/** A bar from the zero line, scaled to [-1, 1], so negative scores read as negative. */
function Bar({ value, tone }: { value: number | null; tone: string }) {
  if (value === null) return <div className="h-2" aria-hidden />;
  const width = `${Math.min(1, Math.abs(value)) * 50}%`;
  return (
    <div className="relative h-2 rounded bg-slate-100 dark:bg-slate-800" aria-hidden>
      <div className="absolute inset-y-0 left-1/2 w-px bg-slate-400" />
      <div
        className={`absolute inset-y-0 rounded ${tone}`}
        style={value >= 0 ? { left: "50%", width } : { right: "50%", width }}
      />
    </div>
  );
}

export function PolicyScores({ data }: { data: RlPolicies }) {
  return (
    <div className="space-y-6">
      <ul className="space-y-4" aria-label="Score per policy">
        {data.policies.map((p) => (
          <li key={p.policy} className="space-y-1">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <span className="font-mono text-sm font-medium text-slate-900 dark:text-white">{p.policy}</span>
              <span className="text-xs text-slate-500 dark:text-slate-400">{p.description}</span>
            </div>
            <Bar value={p.outcome_only_mean} tone="bg-slate-400" />
            <Bar value={p.reward_mean} tone="bg-sky-600" />
          </li>
        ))}
      </ul>
      <p className="flex gap-4 text-xs text-slate-500 dark:text-slate-400">
        <span className="flex items-center gap-1">
          <span className="h-2 w-4 rounded bg-slate-400" aria-hidden /> Outcome only
        </span>
        <span className="flex items-center gap-1">
          <span className="h-2 w-4 rounded bg-sky-600" aria-hidden /> Trajectory-aware
        </span>
      </p>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">Scores per scripted policy, n={data.n}</caption>
          <thead>
            <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:text-slate-400">
              <th className="py-2 pr-4 font-medium">Policy</th>
              <th className="py-2 pr-4 font-medium">Reward</th>
              <th className="py-2 pr-4 font-medium">Outcome only</th>
              <th className="py-2 font-medium">Flag recall</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {data.policies.map((p) => (
              <tr key={p.policy}>
                <td className="py-2 pr-4 font-mono text-xs">{p.policy}</td>
                <td className="py-2 pr-4 tabular-nums">{score(p.reward_mean)}</td>
                <td className="py-2 pr-4 tabular-nums">{score(p.outcome_only_mean)}</td>
                <td className="py-2 tabular-nums">{pct(p.flag_recall)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
