import {
  daysBetween,
  describeCode,
  formatDate,
  formatMoney,
  largestLine,
  latest,
  type Details,
  type Fact,
  type ToolName,
} from "@/lib/evidence";

/** The way a naive surveillance system goes wrong that a case is built to show. */
export type FailureMode = "crying-wolf" | "one-excuse" | "unsupported";

export interface CaseCopy {
  slug: string;
  scenarioId: string;
  /** A short label for lists. */
  title: string;
  /** The slug of the case this one is deliberately paired with. */
  pairWith: string | null;
  failureMode: FailureMode;
  /** The evidence that decides the case, in reading order. The rest is shown as supporting. */
  deciding: ToolName[];
  headline: (facts: Fact[]) => string;
  concerns: (facts: Fact[]) => string[];
  explanations: (facts: Fact[]) => string[];
  whyTricky: string;
}

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;

function roleOf(details: Details): string {
  return details.rptowner_title?.trim() || details.rptowner_relationship;
}

function singleTradeLimit(facts: Fact[]): number | null {
  return latest(facts, "limits")?.data.single_trade_limit ?? null;
}

// Cases 1 and 5 share one trade on purpose: identical on the surface, different in the filing.
function blackoutSaleHeadline(facts: Fact[]): string {
  const details = latest(facts, "details")?.data;
  const material = latest(facts, "material")?.data;
  if (!details) return "A sale before earnings";
  const line = largestLine(details);
  const base = `${roleOf(details)} sells ${formatMoney(line.trans_value)} of stock`;
  if (!material?.event_date) return base;
  const days = daysBetween(line.trans_date, material.event_date);
  return `${base} ${plural(days, "day")} before earnings`;
}

function blackoutSaleConcerns(facts: Fact[]): string[] {
  const material = latest(facts, "material")?.data;
  if (!material?.in_blackout || !material.blackout_start || !material.blackout_end) return [];
  return [
    `The sale falls inside a blackout window (${formatDate(material.blackout_start)} to ${formatDate(material.blackout_end)}) around ${material.event_type ?? "a company"} news on ${formatDate(material.event_date ?? material.blackout_end)}.`,
    "Trading just before results are public is exactly what blackout windows exist to prevent.",
  ];
}

function blackoutSaleExplanations(facts: Fact[]): string[] {
  const details = latest(facts, "details")?.data;
  const out: string[] = [];
  if (details?.reported_under_10b5_1 === "true") {
    out.push(
      "The filing reports the sale was made under a Rule 10b5-1 plan, a trading schedule set up in advance. That is a reported signal, not proof the plan qualifies for the legal defense."
    );
  } else if (details?.reported_under_10b5_1 === "false") {
    out.push("The filing reports the sale was not made under a 10b5-1 plan.");
  } else {
    out.push(
      "The filing doesn't say whether the sale was pre-planned. Its 10b5-1 status is not established, which is different from there being no plan."
    );
  }
  const limit = singleTradeLimit(facts);
  if (details && limit !== null) {
    out.push(
      `Size is not the issue: ${formatMoney(largestLine(details).trans_value)} is well under the ${formatMoney(limit)} single-trade limit for this role.`
    );
  }
  return out;
}

function mixedFilingHeadline(facts: Fact[]): string {
  const details = latest(facts, "details")?.data;
  if (!details) return "A filing with two transaction lines";
  const sale = largestLine(details);
  const withheld = details.transactions.find((t) => t.trans_code === "F" && !t.superseded);
  const role = roleOf(details);
  if (!withheld) return `${role} sells ${formatMoney(sale.trans_value)} of stock`;
  return `${role}'s filing: a ${formatMoney(sale.trans_value)} sale next to a ${formatMoney(withheld.trans_value)} tax withholding`;
}

function mixedFilingConcerns(facts: Fact[]): string[] {
  const details = latest(facts, "details")?.data;
  const limits = latest(facts, "limits")?.data;
  const rolling = latest(facts, "rolling")?.data;
  if (!details || !limits) return [];
  const out: string[] = [];
  const sale = largestLine(details);
  if (sale.trans_value > limits.single_trade_limit) {
    const ratio = Number((sale.trans_value / limits.single_trade_limit).toFixed(1));
    out.push(
      `The ${formatMoney(sale.trans_value)} ${describeCode(sale.trans_code).toLowerCase()} is ${ratio} times the ${formatMoney(limits.single_trade_limit)} single-trade limit for this role.`
    );
  }
  if (rolling && rolling.total_volume > limits.rolling_90d_limit) {
    out.push(
      `Trading in the 90 days up to this date totals ${formatMoney(rolling.total_volume)} against a ${formatMoney(limits.rolling_90d_limit)} limit.`
    );
  }
  return out;
}

function mixedFilingExplanations(facts: Fact[]): string[] {
  const details = latest(facts, "details")?.data;
  const withheld = details?.transactions.find((t) => t.trans_code === "F" && !t.superseded);
  if (!withheld) return [];
  return [
    `One line is ${formatMoney(withheld.trans_value)} of ${describeCode("F").toLowerCase()}: routine, and treated as exempt.`,
    "That exemption covers only that line. It says nothing about the separate sale in the same filing.",
  ];
}

export const CASE_COPY: CaseCopy[] = [
  {
    slug: "blackout-sale",
    scenarioId: "scenario-01-blackout-sale",
    title: "Sale just before earnings",
    pairWith: "planned-sale",
    failureMode: "unsupported",
    deciding: ["get_material_events", "get_transaction_details"],
    headline: blackoutSaleHeadline,
    concerns: blackoutSaleConcerns,
    explanations: blackoutSaleExplanations,
    whyTricky:
      "Selling before earnings is the classic warning sign, but a filing alone can't show whether the insider knew anything. The right outcome is a flag for a human to review, not an accusation.",
  },
  {
    slug: "planned-sale",
    scenarioId: "scenario-05-10b5-1-sale",
    title: "Same sale, pre-arranged plan",
    pairWith: "blackout-sale",
    failureMode: "crying-wolf",
    deciding: ["get_transaction_details", "get_material_events"],
    headline: blackoutSaleHeadline,
    concerns: blackoutSaleConcerns,
    explanations: blackoutSaleExplanations,
    whyTricky:
      "It looks identical to the previous case. The difference is one field in the filing: the sale was reported under a plan set up in advance. A system that flags every pre-earnings sale buries analysts in false alarms.",
  },
  {
    slug: "mixed-filing",
    scenarioId: "scenario-07-f-does-not-clear-s",
    title: "Tax line next to a large sale",
    pairWith: null,
    failureMode: "one-excuse",
    deciding: ["get_transaction_details", "get_applicable_role_limits", "rolling_90d_trading_volume"],
    headline: mixedFilingHeadline,
    concerns: mixedFilingConcerns,
    explanations: mixedFilingExplanations,
    whyTricky:
      "A tax-withholding line is exempt, so a careless system sees an exempt filing and clears all of it, missing a very large sale in the same filing.",
  },
];

export function caseCopyBySlug(slug: string): CaseCopy | undefined {
  return CASE_COPY.find((c) => c.slug === slug);
}

export function caseCopyForScenario(scenarioId: string): CaseCopy | undefined {
  return CASE_COPY.find((c) => c.scenarioId === scenarioId);
}
