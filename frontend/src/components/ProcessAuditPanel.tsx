import { Badge, CheckBadge } from "@/components/ui/Badge";
import { Card, CardTitle } from "@/components/ui/Card";
import { InfoTip } from "@/components/ui/InfoTip";
import { GLOSSARY } from "@/lib/glossary";
import type { ProcessAudit } from "@/lib/schemas";

function Row({
  title,
  tip,
  badge,
  detail,
}: {
  title: string;
  tip: string;
  badge: React.ReactNode;
  detail: string;
}) {
  return (
    <li className="flex flex-wrap items-start justify-between gap-2 py-3 first:pt-0 last:pb-0">
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
          {title}
          <InfoTip text={tip} label={`${title}.`} />
        </p>
        <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{detail}</p>
      </div>
      {badge}
    </li>
  );
}

/** How the investigation reached its finding, checked in code. Never a bare score. */
export function ProcessAuditPanel({ audit }: { audit: ProcessAudit }) {
  const missing = audit.mandatory_tools_missing;
  const total = audit.mandatory_tools_called.length + missing.length;
  const claimed = audit.claimed_exemptions;
  const unsupported = audit.unsupported_exemptions;

  return (
    <Card aria-label="Process audit" className="space-y-3">
      <CardTitle>
        Process audit
        <InfoTip text={GLOSSARY.processAudit} label="Process audit." />
      </CardTitle>
      <p className="text-xs text-slate-500 dark:text-slate-400">
        Checked in code, with no AI judgement. It records how the investigation worked; it never
        changes the finding.
      </p>
      <ul className="divide-y divide-slate-200 dark:divide-slate-800">
        <Row
          title="Required evidence gathered"
          tip="Every investigation must call all six read-only tools: transaction details, role limits, compliance rules, rolling 90-day volume, the insider's baseline, and material events."
          badge={
            <CheckBadge
              ok={missing.length === 0}
              okLabel={`${audit.mandatory_tools_called.length} of ${total} tools`}
              failLabel={`${audit.mandatory_tools_called.length} of ${total} tools`}
            />
          }
          detail={
            missing.length === 0
              ? "Every required tool was called."
              : `Missing: ${missing.join(", ")}.`
          }
        />
        <Row
          title="Transaction details first"
          tip="The details call supplies the arguments every other tool needs, so an investigation that skips it first is working from guesses."
          badge={<CheckBadge ok={audit.details_first} okLabel="Yes" failLabel="No" />}
          detail={
            audit.details_first
              ? "The first call was get_transaction_details."
              : "Another tool was called before the transaction details."
          }
        />
        <Row
          title="Citations all real"
          tip="Each claim must cite a tool call that actually happened in this run."
          badge={<CheckBadge ok={audit.citation_validity === 1} okLabel="All real" failLabel="Problem" />}
          detail={
            audit.fabricated_citation_ids.length > 0
              ? `Cited calls that never happened: ${audit.fabricated_citation_ids.join(", ")}.`
              : audit.citation_validity === 1
                ? "Every claim cites a tool call from this run."
                : "Some claims cite no evidence at all."
          }
        />
        <Row
          title="Exemptions supported"
          tip="An exemption stated in the finding, such as a 10b5-1 plan, tax withholding or an option exercise, must be backed by the filing's own data for that transaction."
          badge={
            claimed.length === 0 ? (
              <Badge variant="slate">None claimed</Badge>
            ) : (
              <CheckBadge ok={unsupported.length === 0} okLabel="Supported" failLabel="Unsupported" />
            )
          }
          detail={
            claimed.length === 0
              ? "The finding claims no exemption."
              : unsupported.length === 0
                ? `Backed by the filing: ${claimed.map((e) => e.kind.replaceAll("_", " ")).join(", ")}.`
                : `Not backed by the filing: ${unsupported.map((e) => e.kind.replaceAll("_", " ")).join(", ")}.`
          }
        />
      </ul>
    </Card>
  );
}
