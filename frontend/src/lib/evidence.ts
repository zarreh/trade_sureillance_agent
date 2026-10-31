import { z } from "zod";

import type { ToolCallRecord } from "@/lib/schemas";

/**
 * Typed views over the raw tool results (src/surveillance/tools). Each record
 * is parsed on its own, so a failed or unexpected result degrades to a "raw"
 * fact that the UI still shows, rather than hiding the evidence.
 */

const TransactionSchema = z.object({
  nonderiv_trans_sk: z.number(),
  trans_date: z.string(),
  trans_code: z.string(),
  trans_shares: z.number(),
  trans_priceper_share: z.number(),
  trans_value: z.number(),
  superseded: z.boolean().default(false),
  superseded_by: z.string().nullable().default(null),
});

const DetailsSchema = z.object({
  accession_number: z.string(),
  issuer_name: z.string(),
  issuer_ticker: z.string().nullable().default(null),
  filing_date: z.string(),
  document_type: z.string(),
  reported_under_10b5_1: z.enum(["true", "false", "unknown"]),
  filing_lag_trading_days: z.number().nullable().default(null),
  rptowner_name: z.string(),
  rptowner_relationship: z.string(),
  rptowner_title: z.string().nullable().default(null),
  transactions: z.array(TransactionSchema),
});

const LimitsSchema = z.object({
  relationship: z.string(),
  authorization_level: z.string(),
  single_trade_limit: z.number(),
  rolling_90d_limit: z.number(),
  blackout_restrictions: z.string(),
});

const RulesSchema = z.array(
  z.object({
    rule_id: z.string(),
    rule_name: z.string(),
    threshold_value: z.number().nullable().default(null),
    rule_type: z.string(),
    severity: z.string(),
  })
);

const RollingSchema = z.object({
  total_volume: z.number(),
  sales_volume: z.number().default(0),
  purchases_volume: z.number().default(0),
  volume_by_code: z.record(z.string(), z.number()).default({}),
  transaction_count: z.number(),
  window_end: z.string(),
  window_days: z.number().default(90),
});

const BaselineSchema = z.object({
  as_of_date: z.string(),
  lookback_days: z.number(),
  transaction_count: z.number(),
  mean_value: z.number().optional(),
  median_value: z.number().optional(),
  max_value: z.number().optional(),
});

const MaterialSchema = z.object({
  on_date: z.string(),
  in_blackout: z.boolean(),
  event_type: z.string().optional(),
  event_date: z.string().optional(),
  blackout_start: z.string().optional(),
  blackout_end: z.string().optional(),
});

export type Transaction = z.infer<typeof TransactionSchema>;
export type Details = z.infer<typeof DetailsSchema>;
export type Limits = z.infer<typeof LimitsSchema>;
export type Rolling = z.infer<typeof RollingSchema>;
export type Baseline = z.infer<typeof BaselineSchema>;
export type Material = z.infer<typeof MaterialSchema>;
export type Rule = z.infer<typeof RulesSchema>[number];

export type ToolName =
  | "get_transaction_details"
  | "get_applicable_role_limits"
  | "get_compliance_rules"
  | "rolling_90d_trading_volume"
  | "insider_trading_baseline"
  | "get_material_events";

export type Fact =
  | { kind: "details"; record: ToolCallRecord; data: Details }
  | { kind: "limits"; record: ToolCallRecord; data: Limits }
  | { kind: "rules"; record: ToolCallRecord; data: Rule[] }
  | { kind: "rolling"; record: ToolCallRecord; data: Rolling }
  | { kind: "baseline"; record: ToolCallRecord; data: Baseline }
  | { kind: "material"; record: ToolCallRecord; data: Material }
  | { kind: "raw"; record: ToolCallRecord };

export type FactKind = Fact["kind"];

const KIND_BY_TOOL: Record<string, Exclude<FactKind, "raw">> = {
  get_transaction_details: "details",
  get_applicable_role_limits: "limits",
  get_compliance_rules: "rules",
  rolling_90d_trading_volume: "rolling",
  insider_trading_baseline: "baseline",
  get_material_events: "material",
};

const SCHEMAS = {
  details: DetailsSchema,
  limits: LimitsSchema,
  rules: RulesSchema,
  rolling: RollingSchema,
  baseline: BaselineSchema,
  material: MaterialSchema,
} as const;

function parseOne(record: ToolCallRecord): Fact {
  const kind = KIND_BY_TOOL[record.tool_name];
  if (!kind) return { kind: "raw", record };
  let json: unknown;
  try {
    json = JSON.parse(record.result);
  } catch {
    return { kind: "raw", record };
  }
  const parsed = SCHEMAS[kind].safeParse(json);
  if (!parsed.success) return { kind: "raw", record };
  return { kind, record, data: parsed.data } as Fact;
}

export function parseEvidence(records: ToolCallRecord[]): Fact[] {
  return records.map(parseOne);
}

/** The latest fact of a kind, as the oracle and the audit also read it. */
export function latest<K extends Exclude<FactKind, "raw">>(
  facts: Fact[],
  kind: K
): Extract<Fact, { kind: K }> | undefined {
  return facts.findLast((f) => f.kind === kind) as Extract<Fact, { kind: K }> | undefined;
}

/** Transaction lines still in force: an amended-away line is not the trade under review. */
export function activeLines(details: Details): Transaction[] {
  const active = details.transactions.filter((t) => !t.superseded);
  return active.length > 0 ? active : details.transactions;
}

export function largestLine(details: Details): Transaction {
  return activeLines(details).reduce((a, b) => (b.trans_value > a.trans_value ? b : a));
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** Hand-formatted: `toLocaleDateString` can differ between server and browser renders. */
export function formatDate(iso: string): string {
  const [year, month, day] = iso.split("-").map(Number);
  return `${MONTHS[month - 1]} ${day}, ${year}`;
}

export function dayNumber(iso: string): number {
  const [year, month, day] = iso.split("-").map(Number);
  return Date.UTC(year, month - 1, day) / 86_400_000;
}

export function daysBetween(fromIso: string, toIso: string): number {
  return dayNumber(toIso) - dayNumber(fromIso);
}

export function formatMoney(value: number): string {
  return `$${Math.round(value).toLocaleString("en-US")}`;
}

export function formatCount(value: number): string {
  return Math.round(value).toLocaleString("en-US");
}

export const TRANSACTION_CODES: Record<string, string> = {
  S: "Sale",
  P: "Purchase",
  F: "Shares withheld for tax",
  M: "Option exercise",
  A: "Grant or award",
  G: "Gift",
};

export function describeCode(code: string): string {
  return TRANSACTION_CODES[code] ?? `Code ${code}`;
}
