export const SUCCESS_FINDING = {
  disposition: "flag",
  severity: "Medium",
  rules_cited: [
    { rule_id: "R005", rule_name: "Suspicious Timing Near Earnings", severity: "Critical" },
  ],
  confidence: "high",
  finding_text:
    "The sale on 2025-07-18 falls within a seeded blackout window ahead of an earnings event.",
  exculpatory_factors: [],
  reported_under_10b5_1: "unknown",
  incomplete: false,
  incomplete_reason: null,
  grounding_report: {
    claims: [{ claim_id: "c1", supported: true, reason: "cited real tool_call_ids" }],
    unsupported: 0,
    confidence: "high",
  },
};

export const SUCCESS_INVESTIGATION = {
  id: "run-success",
  accession_number: "SCENARIO-0000000001-25-000001",
  status: "completed",
  created_at: "2026-08-19T00:00:00Z",
  updated_at: "2026-08-19T00:00:05Z",
  finding_kind: "published",
  finding: SUCCESS_FINDING,
  error: null,
  total_cost_usd: 0.0021,
  costs: [
    { node: "plan", model: "gpt-4o-mini", prompt_tokens: 500, completion_tokens: 50, cost_usd: 0.0001 },
    { node: "draft_finding", model: "gpt-4o", prompt_tokens: 800, completion_tokens: 120, cost_usd: 0.002 },
  ],
};

const NODES = [
  "plan",
  "check_plan",
  "investigate",
  "tools",
  "draft_finding",
  "extract_claims",
  "judge_grounding",
  "publish",
];

export function sseBody(finalPayload: { status: string; finding: unknown }): string {
  const lines = NODES.map((node) => `data: ${JSON.stringify({ node, output: {} })}\n\n`);
  lines.push(`data: ${JSON.stringify({ node: "__end__", output: finalPayload })}\n\n`);
  return lines.join("");
}
