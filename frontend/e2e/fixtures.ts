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
  claims: [
    {
      id: "c1",
      text: "The sale on 2025-07-18 falls within a seeded blackout window.",
      cited_tool_call_ids: ["t1", "t6"],
    },
  ],
  process_audit: {
    mandatory_tools_called: [
      "get_transaction_details",
      "get_applicable_role_limits",
      "get_compliance_rules",
      "rolling_90d_trading_volume",
      "insider_trading_baseline",
      "get_material_events",
    ],
    mandatory_tools_missing: [],
    coverage: 1,
    details_first: true,
    fabricated_citation_ids: [],
    citation_validity: 1,
    claimed_exemptions: [],
    unsupported_exemptions: [],
    exemption_validity: 1,
    trajectory_score: 1,
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

import type { Page } from "@playwright/test";

/** POST /investigations answers 202 with this run id. */
export async function mockStart(page: Page, id: string, delayMs = 0): Promise<void> {
  await page.route("**/investigations", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    if (delayMs) await new Promise((resolve) => setTimeout(resolve, delayMs));
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ id, status: "running" }),
    });
  });
}

/** The stored run: its replayed event stream and its final record. */
export async function mockRun(
  page: Page,
  id: string,
  investigation: Record<string, unknown>,
  streamDelayMs = 0
): Promise<void> {
  await page.route(`**/investigations/${id}/events`, async (route) => {
    if (streamDelayMs) await new Promise((resolve) => setTimeout(resolve, streamDelayMs));
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: sseBody({ status: "completed", finding: investigation.finding as unknown }),
    });
  });
  await page.route(`**/investigations/${id}`, async (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(investigation),
    });
  });
}

/** Collects console errors and uncaught exceptions so a test can assert there are none. */
export function watchConsole(page: Page): string[] {
  const problems: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") problems.push(message.text());
  });
  page.on("pageerror", (error) => problems.push(error.message));
  return problems;
}
