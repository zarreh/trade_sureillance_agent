import { Badge, DispositionBadge } from "@/components/ui/Badge";
import { Card, CardTitle } from "@/components/ui/Card";
import { liveSummary, LIVE_RUN } from "@/lib/case-data";
import type { Case } from "@/lib/schemas";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-0.5 text-sm">
      <dt className="text-xs text-slate-500 dark:text-slate-400">{label}</dt>
      <dd className="text-slate-900 dark:text-slate-100">{children}</dd>
    </div>
  );
}

/** Three views of one case side by side: the answer key, what the AI concluded, and what the checks said about it. */
export function CaseOutcome({ data }: { data: Case }) {
  const live = data.live;
  const summary = live ? liveSummary(live) : null;
  const review = summary !== null && ((summary.unsupported ?? 0) > 0 || summary.uncitedClaims > 0 || summary.fabricatedCitations > 0);

  return (
    <section aria-label="Outcome" className="grid gap-3 md:grid-cols-3">
      <Card className="space-y-3">
        <CardTitle>Answer key</CardTitle>
        <DispositionBadge disposition={data.expected_disposition} />
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Set when the scenario was designed. A rules-based reference investigation reaches it from the evidence.
        </p>
      </Card>

      <Card className="space-y-3">
        <CardTitle>AI investigator</CardTitle>
        {live?.submitted ? (
          <>
            <div className="flex flex-wrap items-center gap-2">
              <DispositionBadge disposition={live.submitted} />
              {live.correct ? (
                <Badge variant="green">Matches the answer key</Badge>
              ) : (
                <Badge variant="red">Differs from the answer key</Badge>
              )}
              {live.incomplete && <Badge variant="amber">Incomplete</Badge>}
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Recorded live run{LIVE_RUN ? ` on ${LIVE_RUN.run_date}` : ""}
              {live.models?.length ? ` using ${live.models.join(" and ")}` : ""}
              {live.cost_usd !== null ? `, costing $${live.cost_usd.toFixed(3)}` : ""}.
            </p>
          </>
        ) : (
          <p className="text-sm text-slate-600 dark:text-slate-300">No live run is recorded for this case.</p>
        )}
      </Card>

      <Card className="space-y-3">
        <CardTitle>What the safeguards reported</CardTitle>
        {summary ? (
          <dl className="space-y-2">
            <Row label="Claims check">
              {summary.unsupported === null
                ? "The run stopped before its draft was judged."
                : `${summary.claimCount - summary.unsupported} of ${summary.claimCount} claims judged supported`}
            </Row>
            <Row label="Citations">
              {summary.fabricatedCitations > 0
                ? `Cites ${summary.fabricatedCitations} tool calls that never happened`
                : summary.uncitedClaims > 0
                  ? `${summary.uncitedClaims} of ${summary.claimCount} claims cite no evidence`
                  : "Every claim cites a real tool call"}
            </Row>
            {summary.checksRun !== null && summary.checksRequired !== null && (
              <Row label="Required checks">{`${summary.checksRun} of ${summary.checksRequired} run`}</Row>
            )}
            {review && <Badge variant="amber">Human review required</Badge>}
            {live?.correct === false && !review && (
              <p className="text-xs leading-relaxed text-slate-600 dark:text-slate-300">
                These checks cover evidence and process, not whether the verdict is right. This run passed them and
                still differs from the answer key.
              </p>
            )}
          </dl>
        ) : (
          <p className="text-sm text-slate-600 dark:text-slate-300">Nothing to report without a live run.</p>
        )}
      </Card>
    </section>
  );
}
