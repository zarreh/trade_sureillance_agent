import { ClaimsCheck } from "./ClaimsCheck";
import { EvidenceCards } from "./EvidenceCards";
import { EvidencePanel } from "./EvidencePanel";
import { ProcessAuditPanel } from "./ProcessAuditPanel";
import { TraceTimeline } from "./TraceTimeline";
import { ValidatorStrip } from "./ValidatorStrip";
import { Callout } from "@/components/ui/Callout";
import type { ToolName } from "@/lib/evidence";
import type { ComplianceFinding, ToolCallRecord } from "@/lib/schemas";

/** One investigation of one case: the evidence it retrieved, what it concluded, and how it was checked. */
export function CaseRunPanel({
  kind,
  finding,
  evidence,
  deciding,
  events,
}: {
  kind: "ai" | "reference";
  finding: ComplianceFinding;
  evidence: ToolCallRecord[];
  deciding: ToolName[];
  events?: { node: string }[];
}) {
  return (
    <div className="space-y-6">
      <Callout variant="info" title={kind === "ai" ? "A recorded run of the AI investigator" : "The reference investigation"}>
        {kind === "ai"
          ? "The conclusion and the claims below were written by the model. The checks beside them are code and a separate judging model."
          : "The same graph, run with a rules-based stand-in instead of an AI model. It shows what a correct, fully grounded investigation looks like. It is not a model result."}
      </Callout>
      <EvidenceCards evidence={evidence} deciding={deciding} />
      <EvidencePanel finding={finding} />
      <ValidatorStrip finding={finding} />
      <ClaimsCheck finding={finding} />
      {finding.process_audit && <ProcessAuditPanel audit={finding.process_audit} />}
      {events && events.length > 0 && (
        <details className="rounded-xl border border-line p-4">
          <summary className="cursor-pointer text-sm font-medium text-fg">
            Under the hood: the steps of this investigation
          </summary>
          <div className="mt-3">
            <TraceTimeline events={events} />
          </div>
        </details>
      )}
    </div>
  );
}
