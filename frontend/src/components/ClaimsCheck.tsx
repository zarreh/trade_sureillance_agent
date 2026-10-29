import { Check, X } from "lucide-react";

import { Card, CardTitle } from "@/components/ui/Card";
import { InfoTip } from "@/components/ui/InfoTip";
import { GLOSSARY } from "@/lib/glossary";
import type { ComplianceFinding } from "@/lib/schemas";

/** Each claim in the draft beside the grounding judge's verdict on it. */
export function ClaimsCheck({ finding }: { finding: ComplianceFinding }) {
  const verdicts = new Map((finding.grounding_report?.claims ?? []).map((c) => [c.claim_id, c]));
  if (finding.claims.length === 0) return null;
  return (
    <Card aria-label="Claims check" className="space-y-3">
      <CardTitle>
        Claims check
        <InfoTip text={GLOSSARY.claim} label="Claim." />
      </CardTitle>
      <ul className="space-y-3">
        {finding.claims.map((claim) => {
          const verdict = verdicts.get(claim.id);
          const supported = verdict?.supported ?? false;
          return (
            <li key={claim.id} className="flex gap-3 text-sm">
              <span
                className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full ${
                  supported
                    ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
                    : "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300"
                }`}
              >
                {supported ? <Check className="h-3 w-3" aria-label="Supported" /> : <X className="h-3 w-3" aria-label="Not supported" />}
              </span>
              <div className="min-w-0 space-y-1">
                <p className="text-slate-800 dark:text-slate-100">{claim.text}</p>
                {verdict && <p className="text-xs text-slate-500 dark:text-slate-400">{verdict.reason}</p>}
                {claim.cited_tool_call_ids.length > 0 && (
                  <p className="flex flex-wrap gap-1">
                    {claim.cited_tool_call_ids.map((id) => (
                      <span
                        key={id}
                        className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                      >
                        {id}
                      </span>
                    ))}
                  </p>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}
