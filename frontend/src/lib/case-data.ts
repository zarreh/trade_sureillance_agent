import casesJson from "@/generated/cases.json";
import { CASE_COPY, type CaseCopy } from "@/lib/cases";
import { parseEvidence, type Fact } from "@/lib/evidence";
import { CasesSchema, type Case } from "@/lib/schemas";

// Server-side only: importing this from a client component would ship the whole file to the browser.
const DATA = CasesSchema.parse(casesJson);

export const LIVE_RUN = DATA.live_run;
export const REFERENCE_SCORER = DATA.reference_scorer;

export interface SampleCase {
  copy: CaseCopy;
  data: Case;
  /** Evidence from the reference run, parsed. */
  facts: Fact[];
  /** 1-based position among the ten canonical scenarios. */
  number: number;
}

/** Cases that have written copy, in scenario order. */
export function sampleCases(): SampleCase[] {
  return DATA.cases.flatMap((data, index) => {
    const copy = CASE_COPY.find((c) => c.scenarioId === data.id);
    return copy
      ? [{ copy, data, facts: parseEvidence(data.reference.evidence), number: index + 1 }]
      : [];
  });
}

export function sampleCase(slug: string): SampleCase | undefined {
  return sampleCases().find((c) => c.copy.slug === slug);
}

/** Every canonical scenario, for the "investigate a filing" quick picks. */
export function scenarioOptions(): { label: string; accession: string }[] {
  return DATA.cases.map((c) => ({ label: c.name, accession: c.accession_number }));
}

export interface LiveSummary {
  claimCount: number;
  unsupported: number | null;
  uncitedClaims: number;
  fabricatedCitations: number;
  checksRun: number | null;
  checksRequired: number | null;
}

/** What the safeguards reported on one recorded live run. */
export function liveSummary(live: NonNullable<Case["live"]>): LiveSummary {
  const finding = live.finding;
  const audit = finding.process_audit;
  return {
    claimCount: finding.claims.length,
    unsupported: finding.grounding_report?.unsupported ?? null,
    uncitedClaims: finding.claims.filter((c) => c.cited_tool_call_ids.length === 0).length,
    fabricatedCitations: audit?.fabricated_citation_ids.length ?? 0,
    checksRun: audit ? audit.mandatory_tools_called.length : null,
    checksRequired: audit ? audit.mandatory_tools_called.length + audit.mandatory_tools_missing.length : null,
  };
}
