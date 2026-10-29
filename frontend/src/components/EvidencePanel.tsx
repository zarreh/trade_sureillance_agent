import { Badge, DispositionBadge } from "@/components/ui/Badge";
import { Card, CardTitle, type CardTone } from "@/components/ui/Card";
import { InfoTip } from "@/components/ui/InfoTip";
import { GLOSSARY } from "@/lib/glossary";
import type { ComplianceFinding } from "@/lib/schemas";

const TONE: Record<ComplianceFinding["disposition"], CardTone> = {
  clear: "emerald",
  flag: "amber",
  escalate: "red",
};

// Never rendered as an absence of a plan: unknown means the filing never
// established it either way (docs/PLAN.md §3.4).
const REPORTED_10B5_1: Record<ComplianceFinding["reported_under_10b5_1"], string> = {
  true: "Reported under a 10b5-1 plan",
  false: "Reported as not under a 10b5-1 plan",
  unknown: "10b5-1 status: not established",
};

export function EvidencePanel({ finding }: { finding: ComplianceFinding }) {
  return (
    <Card aria-label="Finding" tone={TONE[finding.disposition]} className="space-y-4">
      <CardTitle>
        Finding
        <InfoTip text={GLOSSARY.disposition} label="Disposition." />
      </CardTitle>
      <div className="flex flex-wrap items-center gap-2">
        <DispositionBadge disposition={finding.disposition} />
        {finding.severity && <Badge variant="slate">Severity: {finding.severity}</Badge>}
        <Badge variant="slate">Confidence: {finding.confidence}</Badge>
        <Badge variant="sky">
          {REPORTED_10B5_1[finding.reported_under_10b5_1]}
          <InfoTip text={GLOSSARY.reportedUnder10b5_1} label="10b5-1 status." />
        </Badge>
      </div>

      {finding.incomplete && (
        <p className="rounded-lg bg-amber-100 p-3 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-200">
          Incomplete: {finding.incomplete_reason ?? "stopped before reaching a grounded conclusion"}
        </p>
      )}

      <p className="text-[15px] leading-relaxed text-slate-800 dark:text-slate-100">
        {finding.finding_text}
      </p>

      {finding.rules_cited.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Rules cited
          </h3>
          <ul className="mt-1 space-y-1 text-sm">
            {finding.rules_cited.map((rule) => (
              <li key={rule.rule_id}>
                <span className="font-mono text-xs">{rule.rule_id}</span> {rule.rule_name} ({rule.severity})
              </li>
            ))}
          </ul>
        </div>
      )}

      {finding.exculpatory_factors.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Exculpatory factors
            <InfoTip text={GLOSSARY.exculpatoryFactor} label="Exculpatory factors." />
          </h3>
          <ul className="mt-1 space-y-1 text-sm">
            {finding.exculpatory_factors.map((factor, i) => (
              <li key={i}>
                {factor.kind.replaceAll("_", " ")} (transaction {factor.applies_to_transaction_sk})
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}
