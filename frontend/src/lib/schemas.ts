import { z } from "zod";

/**
 * Mirrors src/surveillance/schemas/finding.py + grounding.py. The API types
 * generated from the OpenAPI schema (api-types.ts) type `finding` as a bare
 * `Record<string, unknown>` — Pydantic's schema for it isn't part of the
 * OpenAPI document since it's returned as opaque JSON, not a typed response
 * model. These schemas are the frontend's own source of truth for what's
 * actually inside it, validated at runtime rather than just cast.
 */
export const ExculpatoryKindSchema = z.enum([
  "reported_under_10b5_1",
  "tax_withholding",
  "option_exercise",
  "below_all_thresholds",
]);

export const RuleCitationSchema = z.object({
  rule_id: z.string(),
  rule_name: z.string(),
  severity: z.string(),
});

export const ExculpatoryFactorSchema = z.object({
  kind: ExculpatoryKindSchema,
  evidence_tool_call_id: z.string(),
  applies_to_transaction_sk: z.number(),
});

export const ClaimJudgmentSchema = z.object({
  claim_id: z.string(),
  supported: z.boolean(),
  evidence_span: z.string().nullable().optional(),
  reason: z.string(),
});

export const GroundingReportSchema = z.object({
  claims: z.array(ClaimJudgmentSchema),
  unsupported: z.number(),
  confidence: z.enum(["high", "medium", "low"]),
});

export const ReportedUnder10b51Schema = z.enum(["true", "false", "unknown"]);

export const ClaimedExemptionSchema = z.object({
  kind: ExculpatoryKindSchema,
  transaction_sk: z.number().nullable().optional(),
});

export const ProcessAuditSchema = z.object({
  mandatory_tools_called: z.array(z.string()),
  mandatory_tools_missing: z.array(z.string()),
  coverage: z.number(),
  details_first: z.boolean(),
  fabricated_citation_ids: z.array(z.string()),
  citation_validity: z.number(),
  claimed_exemptions: z.array(ClaimedExemptionSchema),
  unsupported_exemptions: z.array(ClaimedExemptionSchema),
  exemption_validity: z.number(),
  trajectory_score: z.number(),
});

export const ClaimSchema = z.object({
  id: z.string(),
  text: z.string(),
  cited_tool_call_ids: z.array(z.string()).default([]),
});

export const ComplianceFindingSchema = z.object({
  disposition: z.enum(["clear", "flag", "escalate"]),
  severity: z.enum(["Low", "Medium", "High", "Critical"]).nullable().optional(),
  rules_cited: z.array(RuleCitationSchema).default([]),
  confidence: z.enum(["high", "medium", "low"]),
  finding_text: z.string(),
  exculpatory_factors: z.array(ExculpatoryFactorSchema).default([]),
  reported_under_10b5_1: ReportedUnder10b51Schema.default("unknown"),
  incomplete: z.boolean().default(false),
  incomplete_reason: z.string().nullable().optional(),
  // Present only once grounding has run (finding_kind === "published").
  grounding_report: GroundingReportSchema.optional(),
  claims: z.array(ClaimSchema).default([]),
  process_audit: ProcessAuditSchema.nullable().optional(),
});

export type ComplianceFinding = z.infer<typeof ComplianceFindingSchema>;
export type Claim = z.infer<typeof ClaimSchema>;
export type ProcessAudit = z.infer<typeof ProcessAuditSchema>;
export type ExculpatoryFactor = z.infer<typeof ExculpatoryFactorSchema>;
export type GroundingReport = z.infer<typeof GroundingReportSchema>;

/** One node's SSE event (surveillance.api.streaming). */
export const TraceEventSchema = z.object({
  node: z.string(),
  output: z.unknown(),
});
export type TraceEvent = z.infer<typeof TraceEventSchema>;

/** The terminal SSE event's payload (surveillance.api.streaming.stream_investigation_events). */
export const TraceEndOutputSchema = z.object({
  status: z.string(),
  finding: z.record(z.string(), z.unknown()).nullable(),
});

export const ToolCallRecordSchema = z.object({
  tool_call_id: z.string(),
  tool_name: z.string(),
  args: z.record(z.string(), z.unknown()),
  result: z.string(),
});
export type ToolCallRecord = z.infer<typeof ToolCallRecordSchema>;

const DispositionSchema = z.enum(["clear", "flag", "escalate"]);

/** The rules-based answer key run (scripted stand-in), not a model result. */
export const ReferenceRunSchema = z.object({
  events: z.array(z.object({ node: z.string() })),
  finding: ComplianceFindingSchema,
  evidence: z.array(ToolCallRecordSchema),
});

/** One case's recorded live-model run (evals/recordings/live-*). */
export const LiveCaseSchema = z.object({
  submitted: DispositionSchema.nullable(),
  correct: z.boolean().nullable(),
  published: z.boolean().nullable(),
  incomplete: z.boolean().nullable(),
  reward: z.number().nullable(),
  outcome_only: z.number().nullable(),
  trajectory_score: z.number().nullable(),
  tool_calls: z.number().nullable(),
  evidence_passes: z.number().nullable(),
  unsupported_claims: z.number().nullable(),
  cost_usd: z.number().nullable(),
  models: z.array(z.string()).nullable(),
  finding_kind: z.enum(["published", "draft"]),
  finding: ComplianceFindingSchema,
  evidence: z.array(ToolCallRecordSchema),
});
export type LiveCase = z.infer<typeof LiveCaseSchema>;

export const CaseSchema = z.object({
  id: z.string(),
  name: z.string(),
  expected_disposition: DispositionSchema,
  accession_number: z.string(),
  reference: ReferenceRunSchema,
  live: LiveCaseSchema.nullable(),
});
export type Case = z.infer<typeof CaseSchema>;

/** frontend/src/generated/cases.json, written by evals/export_cases.py. */
export const CasesSchema = z.object({
  reference_scorer: z.string(),
  live_run: z
    .object({
      run_date: z.string(),
      n: z.number(),
      models: z.array(z.string()),
      disposition_accuracy: z.number(),
      total_cost_usd: z.number(),
      scorer: z.string(),
      uncertainty: z.string(),
    })
    .nullable(),
  cases: z.array(CaseSchema),
});
export type Cases = z.infer<typeof CasesSchema>;

/** frontend/src/generated/rl-policies.json, written by evals/run_rl.py. */
export const RlPoliciesSchema = z.object({
  n: z.number(),
  scorer: z.string(),
  label_source: z.string(),
  model_version: z.string(),
  run_date: z.string(),
  uncertainty: z.string(),
  gate_margin: z.number(),
  policies: z.array(
    z.object({
      policy: z.string(),
      description: z.string(),
      reward_mean: z.number(),
      outcome_only_mean: z.number().nullable(),
      flag_recall: z.number().nullable(),
      false_positive_rate_on_clear: z.number().nullable(),
    })
  ),
});
export type RlPolicies = z.infer<typeof RlPoliciesSchema>;
