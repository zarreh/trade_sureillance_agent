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
});

export type ComplianceFinding = z.infer<typeof ComplianceFindingSchema>;
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
