import { ClaimsCheck } from "./ClaimsCheck";
import { CostMeter } from "./CostMeter";
import { EvidencePanel } from "./EvidencePanel";
import { ProcessAuditPanel } from "./ProcessAuditPanel";
import { TraceTimeline } from "./TraceTimeline";
import { ValidatorStrip } from "./ValidatorStrip";
import type { InvestigationResponse } from "@/lib/api";
import type { ComplianceFinding } from "@/lib/schemas";

/** One investigation, live or recorded: trace, finding, checks and cost. */
export function InvestigationView({
  events,
  finding,
  investigation,
}: {
  events: { node: string }[];
  finding: ComplianceFinding | null;
  investigation: InvestigationResponse | null;
}) {
  return (
    <div className="space-y-6">
      <TraceTimeline events={events} />
      {finding && (
        <>
          <ValidatorStrip finding={finding} />
          <EvidencePanel finding={finding} />
          <ClaimsCheck finding={finding} />
          {finding.process_audit && <ProcessAuditPanel audit={finding.process_audit} />}
        </>
      )}
      {investigation && <CostMeter investigation={investigation} />}
    </div>
  );
}
