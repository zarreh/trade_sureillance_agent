import { Badge } from "@/components/ui/Badge";
import type { LiveRuns as LiveRunsData } from "@/lib/schemas";

const pct = (v: number) => `${Math.round(v * 100)}%`;
const signed = (v: number) => (v >= 0 ? `+${v.toFixed(2)}` : v.toFixed(2));

type Scenario = LiveRunsData["runs"][number]["scenarios"][number];

/** Why a scenario scored below 1: the wrong answer, the process audit, or both. */
function whyItLost(s: Scenario): string {
  const parts: string[] = [];
  if (!s.correct) parts.push(`answered ${s.submitted ?? "nothing"}, expected ${s.expected}`);
  if (s.trajectory_score < 1) parts.push(`audit ${s.trajectory_score.toFixed(2)}`);
  if (s.unsupported_claims > 0)
    parts.push(`${s.unsupported_claims} unsupported claim${s.unsupported_claims === 1 ? "" : "s"}`);
  return parts.length ? parts.join(" · ") : "full marks";
}

const TH = "px-3 py-2 font-semibold";
const TD = "px-3 py-2";

export function LiveRuns({ data }: { data: LiveRunsData }) {
  const latest = data.runs[0];
  if (!latest) return null;
  return (
    <div className="space-y-6">
      <div className="overflow-x-auto rounded-lg border border-line">
        <table className="w-full min-w-[44rem] text-left text-sm" aria-label="Live-model runs">
          <thead className="border-b border-line bg-surface-2 text-xs uppercase tracking-wider text-muted">
            <tr>
              <th scope="col" className={TH}>Run</th>
              <th scope="col" className={TH}>Claim extractor</th>
              <th scope="col" className={`${TH} text-right`}>Correct</th>
              <th scope="col" className={`${TH} text-right`}>Audit = 0</th>
              <th scope="col" className={`${TH} text-right`}>Unsupported / run</th>
              <th scope="col" className={`${TH} text-right`}>Mean reward</th>
              <th scope="col" className={`${TH} text-right`}>Cost</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line font-mono text-xs tabular">
            {data.runs.map((run) => (
              <tr key={run.run_date}>
                <td className={`${TD} text-fg`}>{run.run_date}</td>
                <td className={TD}>
                  <Badge variant={run.claim_extractor === "v1" ? "slate" : "accent"}>{run.claim_extractor}</Badge>
                </td>
                <td className={`${TD} text-right`}>
                  {Math.round(run.disposition_accuracy * run.n)}/{run.n}
                </td>
                <td className={`${TD} text-right`}>
                  {run.audit_zero_runs}/{run.n}
                </td>
                <td className={`${TD} text-right`}>{run.unsupported_claims_mean.toFixed(1)}</td>
                <td className={`${TD} text-right text-fg`}>{signed(run.reward_mean)}</td>
                <td className={`${TD} text-right`}>${run.total_cost_usd.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <details className="rounded-lg border border-line">
        <summary className="cursor-pointer px-3 py-2 text-sm font-medium text-fg">
          Per scenario, newest run ({latest.run_date}): why each one lost points
        </summary>
        <div className="overflow-x-auto border-t border-line">
          <table className="w-full min-w-[40rem] text-left text-sm" aria-label="Per-scenario live results">
            <thead className="bg-surface-2 text-xs uppercase tracking-wider text-muted">
              <tr>
                <th scope="col" className={TH}>Scenario</th>
                <th scope="col" className={`${TH} text-right`}>Reward</th>
                <th scope="col" className={TH}>Why</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line text-xs">
              {latest.scenarios.map((s) => (
                <tr key={s.scenario_id}>
                  <td className={`${TD} font-mono text-fg`}>{s.scenario_id.replace(/^scenario-/, "")}</td>
                  <td className={`${TD} text-right font-mono tabular`}>{signed(s.reward)}</td>
                  <td className={`${TD} ${s.correct ? "text-muted" : "text-fg"}`}>{whyItLost(s)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>

      <p className="text-xs text-muted">
        n={latest.n} per run, one run each, labels designed with the scenarios. Disposition accuracy{" "}
        {pct(latest.disposition_accuracy)} in the newest run. Uncertainty: {latest.uncertainty}. Models: {latest.models.join(", ")}.
        Not gated: no CI check depends on these numbers.
      </p>
    </div>
  );
}
