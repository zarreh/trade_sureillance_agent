import { Callout } from "@/components/ui/Callout";
import { InfoTip } from "@/components/ui/InfoTip";
import { GLOSSARY } from "@/lib/glossary";
import type { ComplianceFinding } from "@/lib/schemas";

export function ValidatorStrip({ finding }: { finding: ComplianceFinding }) {
  const report = finding.grounding_report;

  if (!report) {
    return (
      <Callout variant="info" role="status">
        No grounding pass completed. This investigation stopped before its draft was judged.
      </Callout>
    );
  }

  const supported = report.claims.length - report.unsupported;
  return (
    <Callout variant={report.unsupported === 0 ? "success" : "warning"} role="status">
      <span>
        Grounding: {supported}/{report.claims.length} claims supported, confidence: {report.confidence}
        {report.unsupported > 0 && `, ${report.unsupported} unsupported`}
        <InfoTip text={GLOSSARY.grounding} label="Grounding." />
      </span>
    </Callout>
  );
}
