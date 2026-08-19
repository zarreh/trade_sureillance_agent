import type { ComplianceFinding } from "@/lib/schemas";

const DISPOSITION_STYLES: Record<ComplianceFinding["disposition"], string> = {
  clear: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  flag: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
  escalate: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
};

const REPORTED_10B5_1_LABELS: Record<ComplianceFinding["reported_under_10b5_1"], string> = {
  true: "Reported under a 10b5-1 plan",
  false: "Not reported under a 10b5-1 plan",
  // Never rendered as an absence of a plan — unknown means the filing simply
  // never established it either way (docs/PLAN.md §3.4).
  unknown: "10b5-1 status: not established",
};

export function EvidencePanel({ finding }: { finding: ComplianceFinding }) {
  return (
    <section aria-label="Finding" className="space-y-3 rounded border border-neutral-200 p-4 dark:border-neutral-800">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`rounded px-2 py-1 text-xs font-semibold uppercase ${DISPOSITION_STYLES[finding.disposition]}`}
        >
          {finding.disposition}
        </span>
        {finding.severity && (
          <span className="text-xs text-neutral-500">Severity: {finding.severity}</span>
        )}
        <span className="text-xs text-neutral-500">Confidence: {finding.confidence}</span>
        <span className="rounded border border-neutral-300 px-2 py-0.5 text-xs text-neutral-600 dark:border-neutral-700 dark:text-neutral-300">
          {REPORTED_10B5_1_LABELS[finding.reported_under_10b5_1]}
        </span>
      </div>

      {finding.incomplete && (
        <p className="rounded bg-amber-50 p-2 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-200">
          Incomplete: {finding.incomplete_reason ?? "stopped before reaching a grounded conclusion"}
        </p>
      )}

      <p className="text-sm">{finding.finding_text}</p>

      {finding.rules_cited.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold uppercase text-neutral-500">Rules cited</h3>
          <ul className="mt-1 space-y-1 text-sm">
            {finding.rules_cited.map((rule) => (
              <li key={rule.rule_id}>
                <span className="font-mono text-xs">{rule.rule_id}</span> {rule.rule_name} (
                {rule.severity})
              </li>
            ))}
          </ul>
        </div>
      )}

      {finding.exculpatory_factors.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold uppercase text-neutral-500">
            Exculpatory factors
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
    </section>
  );
}
