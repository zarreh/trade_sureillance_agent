import {
  daysBetween,
  describeCode,
  FILING_DEADLINE_TRADING_DAYS,
  formatCount,
  formatDate,
  formatMoney,
  largestLine,
  latest,
  roleOf,
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
  failureMode: FailureMode | null;
  /** The evidence that decides the case, in reading order. The rest is shown as supporting. */
  deciding: ToolName[];
  headline: (facts: Fact[]) => string;
  concerns: (facts: Fact[]) => string[];
  explanations: (facts: Fact[]) => string[];
  whyTricky: string;
}

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;

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

function limitConcerns(facts: Fact[]): string[] {
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

function sizeVsLimit(facts: Fact[]): string | null {
  const details = latest(facts, "details")?.data;
  const limit = singleTradeLimit(facts);
  if (!details || limit === null) return null;
  const value = largestLine(details).trans_value;
  if (value > limit) return null;
  return `At ${formatMoney(value)}, the trade is under the ${formatMoney(limit)} single-trade limit for this role.`;
}

function noExemption(facts: Fact[]): string | null {
  const details = latest(facts, "details")?.data;
  if (!details) return null;
  const line = largestLine(details);
  if (line.trans_code !== "S" && line.trans_code !== "P") return null;
  if (details.reported_under_10b5_1 === "true") return null;
  return details.reported_under_10b5_1 === "false"
    ? "Nothing in the filing offers an exemption: it is an ordinary trade, reported as not under a 10b5-1 plan."
    : "Nothing in the filing offers an exemption: it is an ordinary trade and its 10b5-1 status is not established.";
}

const present = (items: (string | null)[]): string[] => items.filter((s): s is string => s !== null);

function firstSaleHeadline(facts: Fact[]): string {
  const details = latest(facts, "details")?.data;
  const baseline = latest(facts, "baseline")?.data;
  if (!details) return "A large sale with no history";
  const line = largestLine(details);
  const base = `${roleOf(details)} sells ${formatCount(line.trans_shares)} shares for ${formatMoney(line.trans_value)}`;
  return baseline?.transaction_count === 0 ? `${base}, with no trading history to compare` : base;
}

function firstSaleConcerns(facts: Fact[]): string[] {
  const details = latest(facts, "details")?.data;
  const spike = latest(facts, "rules")?.data.find((r) => r.rule_type === "volume_spike");
  const baseline = latest(facts, "baseline")?.data;
  const out: string[] = [];
  if (details && spike?.threshold_value) {
    const shares = largestLine(details).trans_shares;
    if (shares > spike.threshold_value) {
      out.push(
        `${formatCount(shares)} shares is above the ${formatCount(spike.threshold_value)}-share level the firm treats as a volume spike (rule ${spike.rule_id}).`
      );
    }
  }
  if (baseline?.transaction_count === 0) {
    out.push("There are no earlier trades on record to show whether this is normal for this insider.");
  }
  return out;
}

function overLimitHeadline(facts: Fact[]): string {
  const details = latest(facts, "details")?.data;
  if (!details) return "A trade above the role's limit";
  return `${roleOf(details)} sells ${formatMoney(largestLine(details).trans_value)} of stock in one trade`;
}

function lateFilingHeadline(facts: Fact[]): string {
  const details = latest(facts, "details")?.data;
  if (!details) return "A filing reported late";
  const base = `${roleOf(details)}'s ${formatMoney(largestLine(details).trans_value)} sale was reported`;
  const lag = details.filing_lag_trading_days;
  return lag === null ? `${base} late` : `${base} ${plural(lag, "trading day")} after the trade`;
}

function lateFilingConcerns(facts: Fact[]): string[] {
  const lag = latest(facts, "details")?.data.filing_lag_trading_days;
  if (lag === null || lag === undefined || lag <= FILING_DEADLINE_TRADING_DAYS) return [];
  return [
    `The filing arrived ${plural(lag, "trading day")} after the trade. The Section 16(a) deadline is ${FILING_DEADLINE_TRADING_DAYS}.`,
    "Reporting is how the public learns about insider trades, so a late report delays that.",
  ];
}

function taxWithholdingHeadline(facts: Fact[]): string {
  const details = latest(facts, "details")?.data;
  if (!details) return "A tax-withholding filing";
  const line = largestLine(details);
  return line.trans_code === "F"
    ? `${roleOf(details)}'s filing shows ${formatMoney(line.trans_value)} of shares withheld to pay tax`
    : `${roleOf(details)} disposes of ${formatMoney(line.trans_value)} of stock`;
}

function taxWithholdingConcerns(facts: Fact[]): string[] {
  const details = latest(facts, "details")?.data;
  return details ? [`A ${formatMoney(largestLine(details).trans_value)} disposition is large in dollar terms.`] : [];
}

function taxWithholdingExplanations(facts: Fact[]): string[] {
  const details = latest(facts, "details")?.data;
  const isTax = details ? largestLine(details).trans_code === "F" : false;
  return present([
    isTax
      ? "Code F means shares were withheld to cover a tax bill, not sold on the market. It is routine, and treated as exempt."
      : null,
    sizeVsLimit(facts),
  ]);
}

function rollingVolumeHeadline(facts: Fact[]): string {
  const details = latest(facts, "details")?.data;
  const rolling = latest(facts, "rolling")?.data;
  if (!details) return "Sales that add up";
  const base = `${roleOf(details)} sells ${formatMoney(largestLine(details).trans_value)}`;
  return rolling
    ? `${base}, bringing the last ${rolling.window_days} days to ${formatMoney(rolling.total_volume)}`
    : base;
}

function rollingVolumeConcerns(facts: Fact[]): string[] {
  const baseline = latest(facts, "baseline")?.data;
  const out = limitConcerns(facts);
  if (out.length > 0 && baseline?.max_value !== undefined && baseline.transaction_count > 0) {
    out.push(`The total includes an earlier ${formatMoney(baseline.max_value)} trade by the same insider.`);
  }
  return out;
}

function amendmentHeadline(facts: Fact[]): string {
  const details = latest(facts, "details")?.data;
  if (!details) return "An amended filing";
  const sale = `${formatMoney(largestLine(details).trans_value)} sale`;
  return details.document_type === "4"
    ? `${roleOf(details)} reports a ${sale}`
    : `${roleOf(details)} files an amendment (Form ${details.document_type}) for a ${sale}`;
}

function amendmentConcerns(facts: Fact[]): string[] {
  return latest(facts, "details")?.data.document_type === "4"
    ? []
    : ["Amendments can change what was first reported, so the earlier version has to be accounted for."];
}

function amendmentExplanations(facts: Fact[]): string[] {
  const amended = latest(facts, "details")?.data.document_type !== "4";
  return present([
    sizeVsLimit(facts),
    amended
      ? "Replaced filings are kept on record but left out of the totals, so an earlier version does not drive the result."
      : null,
  ]);
}

function ordinaryTradeHeadline(facts: Fact[]): string {
  const details = latest(facts, "details")?.data;
  if (!details) return "An ordinary trade";
  const line = largestLine(details);
  const verb = line.trans_code === "P" ? "buys" : line.trans_code === "S" ? "sells" : "trades";
  return `${roleOf(details)} ${verb} ${formatMoney(line.trans_value)} of stock`;
}

function ordinaryTradeExplanations(facts: Fact[]): string[] {
  const details = latest(facts, "details")?.data;
  const material = latest(facts, "material")?.data;
  const lag = details?.filing_lag_trading_days;
  return present([
    sizeVsLimit(facts),
    lag !== null && lag !== undefined && lag <= FILING_DEADLINE_TRADING_DAYS
      ? `Filed ${plural(lag, "trading day")} after the trade, within the ${FILING_DEADLINE_TRADING_DAYS}-day deadline.`
      : null,
    material && !material.in_blackout ? "No blackout window covers the trade date." : null,
  ]);
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
    slug: "first-large-sale",
    scenarioId: "scenario-02-volume-spike",
    title: "Large sale, no history",
    pairWith: null,
    failureMode: null,
    deciding: ["insider_trading_baseline", "get_compliance_rules", "get_transaction_details"],
    headline: firstSaleHeadline,
    concerns: firstSaleConcerns,
    explanations: (facts) =>
      present([
        sizeVsLimit(facts),
        "This may simply be the first sale the insider has reported. One trade with no history is a reason to look, not evidence of wrongdoing.",
      ]),
    whyTricky:
      "The rule behind this flag compares a trade with the insider's own past, but there is no past here. A trustworthy system says plainly that it has nothing to compare against instead of inventing a baseline.",
  },
  {
    slug: "over-limit-sale",
    scenarioId: "scenario-03-over-limit",
    title: "Sale far above the limit",
    pairWith: null,
    failureMode: null,
    deciding: ["get_applicable_role_limits", "get_transaction_details"],
    headline: overLimitHeadline,
    concerns: limitConcerns,
    explanations: (facts) => present([noExemption(facts)]),
    whyTricky:
      "The clearest alert in the set: one trade far above what the role may do in a single trade. It calls for escalation, not just a routine flag.",
  },
  {
    slug: "late-filing",
    scenarioId: "scenario-04-late-filing",
    title: "Filed late",
    pairWith: null,
    failureMode: null,
    deciding: ["get_transaction_details"],
    headline: lateFilingHeadline,
    concerns: lateFilingConcerns,
    explanations: (facts) =>
      present([
        sizeVsLimit(facts),
        "A late report is a paperwork problem. It does not by itself show the trade was improper.",
      ]),
    whyTricky:
      "Nothing about the trade itself looks suspicious. The problem is the paperwork, so a system that only weighs size and timing would let it through.",
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
    slug: "tax-withholding",
    scenarioId: "scenario-06-tax-withholding",
    title: "Large tax withholding",
    pairWith: "mixed-filing",
    failureMode: "crying-wolf",
    deciding: ["get_transaction_details"],
    headline: taxWithholdingHeadline,
    concerns: taxWithholdingConcerns,
    explanations: taxWithholdingExplanations,
    whyTricky:
      "Large and a disposition are both alarming words. But this is shares withheld to pay tax, which is routine. Flagging it would be a false alarm.",
  },
  {
    slug: "mixed-filing",
    scenarioId: "scenario-07-f-does-not-clear-s",
    title: "Tax line next to a large sale",
    pairWith: "tax-withholding",
    failureMode: "one-excuse",
    deciding: ["get_transaction_details", "get_applicable_role_limits", "rolling_90d_trading_volume"],
    headline: mixedFilingHeadline,
    concerns: limitConcerns,
    explanations: mixedFilingExplanations,
    whyTricky:
      "A tax-withholding line is exempt, so a careless system sees an exempt filing and clears all of it, missing a very large sale in the same filing.",
  },
  {
    slug: "rolling-volume",
    scenarioId: "scenario-08-rolling-90d-over-limit",
    title: "Sales that add up",
    pairWith: null,
    failureMode: null,
    deciding: ["rolling_90d_trading_volume", "get_applicable_role_limits", "insider_trading_baseline"],
    headline: rollingVolumeHeadline,
    concerns: rollingVolumeConcerns,
    explanations: (facts) => present([sizeVsLimit(facts)]),
    whyTricky:
      "This trade alone is within the single-trade limit. It only looks wrong once it is added to what the same insider sold earlier, which means checking across more than one filing.",
  },
  {
    slug: "amended-filing",
    scenarioId: "scenario-09-amend-away",
    title: "Amendment replaces a flagged trade",
    pairWith: null,
    failureMode: null,
    deciding: ["get_transaction_details"],
    headline: amendmentHeadline,
    concerns: amendmentConcerns,
    explanations: amendmentExplanations,
    whyTricky:
      "In this sample, an earlier version of the filing reported a much larger trade before it was corrected. A system that reads every version would still flag it. Counting only the latest record is the right behavior.",
  },
  {
    slug: "ordinary-purchase",
    scenarioId: "scenario-10-ordinary-purchase",
    title: "Ordinary purchase",
    pairWith: null,
    failureMode: null,
    deciding: ["get_transaction_details", "get_applicable_role_limits"],
    headline: ordinaryTradeHeadline,
    concerns: () => [],
    explanations: ordinaryTradeExplanations,
    whyTricky: "The control case: nothing here should raise an alert. A system that flags this flags everything.",
  },
];

export function caseCopyBySlug(slug: string): CaseCopy | undefined {
  return CASE_COPY.find((c) => c.slug === slug);
}

export function caseCopyForScenario(scenarioId: string): CaseCopy | undefined {
  return CASE_COPY.find((c) => c.scenarioId === scenarioId);
}

export const FAILURE_MODES: Record<
  FailureMode,
  { title: string; problem: string; safeguard: string; caseSlug: string }
> = {
  "crying-wolf": {
    title: "Crying wolf",
    problem:
      "Flag every sale made before earnings and analysts drown in alerts, including sales reported under a plan set up in advance.",
    safeguard:
      "The filing's reported 10b5-1 status is read from the data and shown as a signal. It is never guessed from its absence.",
    caseSlug: "planned-sale",
  },
  "one-excuse": {
    title: "One excuse covering everything",
    problem:
      "Tax withholding is routine. If one exempt line clears the whole filing, a very large sale in the same filing goes unnoticed.",
    safeguard: "Exemptions are tied to the specific transaction line they belong to.",
    caseSlug: "mixed-filing",
  },
  unsupported: {
    title: "Confident but unsupported",
    problem: "An AI can write a convincing conclusion that its evidence does not back up.",
    safeguard:
      "The draft is split into claims, each checked against the evidence gathered, and a process audit records whether claims cite real tool calls.",
    caseSlug: "blackout-sale",
  },
};

/** The facts a reader sees first, in plain words. Deliberately leaves out the trading plan. */
export function tradeRows(facts: Fact[]): { label: string; value: string }[] {
  const details = latest(facts, "details")?.data;
  const material = latest(facts, "material")?.data;
  if (!details) return [];
  const line = largestLine(details);
  const rows = [
    { label: "Insider", value: roleOf(details) },
    { label: "Trade", value: `${describeCode(line.trans_code)} of ${formatMoney(line.trans_value)}` },
    { label: "Date", value: formatDate(line.trans_date) },
  ];
  if (material?.event_date) {
    const days = daysBetween(line.trans_date, material.event_date);
    const eventType = material.event_type ?? "announcement";
    rows.push({
      label: "Company news",
      value: `${eventType[0].toUpperCase()}${eventType.slice(1)} on ${formatDate(material.event_date)} (${plural(days, "day")} later)`,
    });
  }
  if (material) rows.push({ label: "Blackout window", value: material.in_blackout ? "Trade falls inside it" : "Trade is outside it" });
  return rows;
}
