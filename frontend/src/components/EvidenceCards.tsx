import type { ReactNode } from "react";

import { REPORTED_10B5_1 } from "./EvidencePanel";
import { Badge, type BadgeVariant } from "@/components/ui/Badge";
import {
  dayNumber,
  describeCode,
  formatCount,
  formatDate,
  formatMoney,
  largestLine,
  latest,
  parseEvidence,
  type Fact,
  type ToolName,
} from "@/lib/evidence";
import type { ToolCallRecord } from "@/lib/schemas";

const FILING_DEADLINE_TRADING_DAYS = 2;

type Status = { label: string; variant: BadgeVariant };
type CardContent = { title: string; status?: Status; body: ReactNode };

/** A trade value against a limit. The marker is the limit; the fill turns red once it is passed. */
function LimitBar({
  value,
  limit,
  valueLabel,
  limitLabel,
}: {
  value: number;
  limit: number;
  valueLabel: string;
  limitLabel: string;
}) {
  const max = Math.max(value, limit) * 1.08 || 1;
  const over = value > limit;
  return (
    <div className="space-y-1">
      <div
        role="img"
        aria-label={`${valueLabel}, compared with ${limitLabel}`}
        className="relative h-3 rounded-full bg-slate-100 dark:bg-slate-800"
      >
        <div
          className={`h-full rounded-full ${over ? "bg-red-500" : "bg-sky-500"}`}
          style={{ width: `${(value / max) * 100}%` }}
        />
        <div
          className="absolute -top-0.5 h-4 w-0.5 bg-slate-900 dark:bg-white"
          style={{ left: `${(limit / max) * 100}%` }}
        />
      </div>
      <div className="flex justify-between gap-3 text-xs text-slate-600 dark:text-slate-300">
        <span>{valueLabel}</span>
        <span>{limitLabel}</span>
      </div>
    </div>
  );
}

/** Blackout window, news date and trade date on one axis. A text line below repeats it for screen readers. */
function Timeline({
  tradeDate,
  start,
  end,
  eventDate,
}: {
  tradeDate: string;
  start: string;
  end: string;
  eventDate?: string;
}) {
  const days = [tradeDate, start, end, ...(eventDate ? [eventDate] : [])].map(dayNumber);
  const min = Math.min(...days) - 3;
  const span = Math.max(...days) + 3 - min;
  const pct = (iso: string) => `${((dayNumber(iso) - min) / span) * 100}%`;
  return (
    <div aria-hidden className="relative mx-3 mb-6 mt-7 h-2 rounded-full bg-slate-200 dark:bg-slate-700">
      <div
        className="absolute h-2 rounded-full bg-amber-400/70"
        style={{ left: pct(start), width: `${((dayNumber(end) - dayNumber(start)) / span) * 100}%` }}
      />
      {eventDate && (
        <div className="absolute top-3 -translate-x-1/2 text-center" style={{ left: pct(eventDate) }}>
          <div className="mx-auto h-2 w-2 rotate-45 bg-slate-700 dark:bg-slate-200" />
          <div className="whitespace-nowrap text-[11px] text-slate-600 dark:text-slate-300">
            News {formatDate(eventDate)}
          </div>
        </div>
      )}
      <div className="absolute -top-6 -translate-x-1/2 text-center" style={{ left: pct(tradeDate) }}>
        <div className="whitespace-nowrap text-[11px] font-medium text-slate-900 dark:text-white">
          Trade {formatDate(tradeDate)}
        </div>
        <div className="mx-auto h-3 w-3 translate-y-1 rounded-full bg-red-500 ring-2 ring-white dark:ring-slate-900" />
      </div>
    </div>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-wrap justify-between gap-x-4 gap-y-0.5 text-sm">
      <dt className="text-slate-500 dark:text-slate-400">{label}</dt>
      <dd className="text-right text-slate-900 dark:text-slate-100">{children}</dd>
    </div>
  );
}

function content(fact: Fact, facts: Fact[]): CardContent {
  switch (fact.kind) {
    case "details": {
      const d = fact.data;
      const lag = d.filing_lag_trading_days;
      const late = lag !== null && lag > FILING_DEADLINE_TRADING_DAYS;
      return {
        title: "The trade as filed",
        status:
          lag === null
            ? undefined
            : late
              ? { label: `Filed ${lag} trading days late`, variant: "amber" }
              : { label: "Filed on time", variant: "green" },
        body: (
          <div className="space-y-3">
            <p className="text-sm text-slate-700 dark:text-slate-200">
              {d.rptowner_name}, {d.rptowner_title?.trim() || d.rptowner_relationship} of {d.issuer_name}
              {d.issuer_ticker ? ` (${d.issuer_ticker})` : ""}
            </p>
            <ul className="space-y-1.5">
              {d.transactions.map((t) => (
                <li
                  key={t.nonderiv_trans_sk}
                  className="flex flex-wrap items-baseline justify-between gap-x-3 rounded-lg bg-slate-50 px-3 py-2 text-sm dark:bg-slate-800/60"
                >
                  <span className="font-medium text-slate-900 dark:text-slate-100">
                    <span className="mr-2 rounded bg-slate-200 px-1.5 py-0.5 font-mono text-xs dark:bg-slate-700">
                      {t.trans_code}
                    </span>
                    {describeCode(t.trans_code)}
                  </span>
                  <span className={t.superseded ? "text-slate-400 line-through" : "text-slate-700 dark:text-slate-200"}>
                    {formatCount(t.trans_shares)} shares × ${t.trans_priceper_share} = {formatMoney(t.trans_value)}
                  </span>
                  <span className="basis-full text-xs text-slate-500 dark:text-slate-400">
                    {formatDate(t.trans_date)}
                    {t.superseded && " · replaced by an amended filing"}
                  </span>
                </li>
              ))}
            </ul>
            <dl className="space-y-1">
              <Row label="Filed">
                {formatDate(d.filing_date)} (Form {d.document_type})
                {lag !== null && `, ${lag} trading day${lag === 1 ? "" : "s"} after the trade`}
              </Row>
              <Row label="Trading plan">{REPORTED_10B5_1[d.reported_under_10b5_1]}</Row>
            </dl>
          </div>
        ),
      };
    }
    case "limits": {
      const l = fact.data;
      const details = latest(facts, "details")?.data;
      const line = details ? largestLine(details) : null;
      const over = line ? line.trans_value > l.single_trade_limit : false;
      return {
        title: "What this role may trade",
        status: line ? (over ? { label: "Over the limit", variant: "red" } : { label: "Within the limit", variant: "green" }) : undefined,
        body: (
          <div className="space-y-3">
            {line && (
              <LimitBar
                value={line.trans_value}
                limit={l.single_trade_limit}
                valueLabel={`Largest trade: ${formatMoney(line.trans_value)}`}
                limitLabel={`Single-trade limit: ${formatMoney(l.single_trade_limit)}`}
              />
            )}
            <dl className="space-y-1">
              <Row label="Role">
                {l.relationship} ({l.authorization_level})
              </Row>
              <Row label="Single-trade limit">{formatMoney(l.single_trade_limit)}</Row>
              <Row label="Rolling 90-day limit">{formatMoney(l.rolling_90d_limit)}</Row>
              <Row label="Blackout restrictions">{l.blackout_restrictions}</Row>
            </dl>
          </div>
        ),
      };
    }
    case "rolling": {
      const r = fact.data;
      const limit = latest(facts, "limits")?.data.rolling_90d_limit;
      const over = limit !== undefined && r.total_volume > limit;
      return {
        title: `Total traded in the ${r.window_days} days before`,
        status: limit === undefined ? undefined : over ? { label: "Over the limit", variant: "red" } : { label: "Within the limit", variant: "green" },
        body: (
          <div className="space-y-3">
            {limit !== undefined && (
              <LimitBar
                value={r.total_volume}
                limit={limit}
                valueLabel={`Total: ${formatMoney(r.total_volume)}`}
                limitLabel={`Rolling limit: ${formatMoney(limit)}`}
              />
            )}
            <dl className="space-y-1">
              <Row label="Window ending">{formatDate(r.window_end)}</Row>
              <Row label="Transactions counted">{r.transaction_count}</Row>
              {Object.entries(r.volume_by_code).map(([code, value]) => (
                <Row key={code} label={describeCode(code)}>
                  {formatMoney(value)}
                </Row>
              ))}
            </dl>
          </div>
        ),
      };
    }
    case "baseline": {
      const b = fact.data;
      const details = latest(facts, "details")?.data;
      if (b.transaction_count === 0) {
        return {
          title: "Their own trading history",
          status: { label: "No history to compare", variant: "slate" },
          body: (
            <p className="text-sm text-slate-700 dark:text-slate-200">
              No earlier trades by this insider were found in the {b.lookback_days} days before this one, so there is
              nothing to compare it against.
            </p>
          ),
        };
      }
      const median = b.median_value;
      const line = details ? largestLine(details) : null;
      return {
        title: "Their own trading history",
        body: (
          <dl className="space-y-1">
            <Row label="Earlier trades">
              {b.transaction_count} in {b.lookback_days} days
            </Row>
            {b.median_value !== undefined && <Row label="Typical trade (median)">{formatMoney(b.median_value)}</Row>}
            {b.max_value !== undefined && <Row label="Largest earlier trade">{formatMoney(b.max_value)}</Row>}
            {line && median ? (
              <Row label="This trade vs typical">{Number((line.trans_value / median).toFixed(1))}×</Row>
            ) : null}
          </dl>
        ),
      };
    }
    case "material": {
      const m = fact.data;
      if (!m.in_blackout || !m.blackout_start || !m.blackout_end) {
        return {
          title: "Was news about to come out?",
          status: { label: "No blackout window", variant: "green" },
          body: (
            <p className="text-sm text-slate-700 dark:text-slate-200">
              No scheduled blackout window covers {formatDate(m.on_date)}.
            </p>
          ),
        };
      }
      return {
        title: "Was news about to come out?",
        status: { label: "Inside a blackout window", variant: "amber" },
        body: (
          <div>
            <Timeline tradeDate={m.on_date} start={m.blackout_start} end={m.blackout_end} eventDate={m.event_date} />
            <p className="text-sm text-slate-700 dark:text-slate-200">
              Trade on {formatDate(m.on_date)}. The blackout runs {formatDate(m.blackout_start)} to{" "}
              {formatDate(m.blackout_end)}
              {m.event_date ? `, around ${m.event_type ?? "company"} news on ${formatDate(m.event_date)}` : ""}.
            </p>
          </div>
        ),
      };
    }
    case "rules":
      return {
        title: "Firm rules checked",
        body: (
          <ul className="space-y-1 text-sm">
            {fact.data.map((rule) => (
              <li key={rule.rule_id} className="flex flex-wrap justify-between gap-x-3">
                <span>
                  <span className="mr-2 font-mono text-xs">{rule.rule_id}</span>
                  {rule.rule_name}
                </span>
                <span className="text-xs text-slate-500 dark:text-slate-400">{rule.severity}</span>
              </li>
            ))}
          </ul>
        ),
      };
    case "raw":
      return {
        title: fact.record.tool_name.replaceAll("_", " "),
        status: { label: "Not summarised", variant: "slate" },
        body: (
          <p className="text-sm text-slate-700 dark:text-slate-200">
            This result could not be summarised. The source result below is what the investigator saw.
          </p>
        ),
      };
  }
}

function prettyJson(text: string): string {
  try {
    return JSON.stringify(JSON.parse(text), null, 2);
  } catch {
    return text;
  }
}

function EvidenceCard({ fact, facts }: { fact: Fact; facts: Fact[] }) {
  const { title, status, body } = content(fact, facts);
  const { record } = fact;
  return (
    <article
      id={`evidence-${record.tool_call_id}`}
      aria-label={title}
      className="scroll-mt-20 space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm target:ring-2 target:ring-sky-500 dark:border-slate-800 dark:bg-slate-900"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white">{title}</h3>
        {status && <Badge variant={status.variant}>{status.label}</Badge>}
      </div>
      {body}
      <details className="text-xs text-slate-500 dark:text-slate-400">
        <summary className="cursor-pointer select-none">
          View source result <span className="ml-1 font-mono">{record.tool_call_id}</span>
        </summary>
        <p className="mt-2 font-mono">
          {record.tool_name}({JSON.stringify(record.args)})
        </p>
        <pre className="mt-1 max-h-64 overflow-auto rounded-lg bg-slate-50 p-3 font-mono text-[11px] leading-relaxed dark:bg-slate-950">
          {prettyJson(record.result)}
        </pre>
      </details>
    </article>
  );
}

function Group({ label, facts, all }: { label: string; facts: Fact[]; all: Fact[] }) {
  if (facts.length === 0) return null;
  return (
    <section aria-label={label} className="space-y-3">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</h2>
      <div className="grid gap-3 md:grid-cols-2">
        {facts.map((fact) => (
          <EvidenceCard key={fact.record.tool_call_id} fact={fact} facts={all} />
        ))}
      </div>
    </section>
  );
}

/**
 * The evidence the investigator retrieved, one card per tool call. Every card
 * is anchored by its tool_call_id so a claim's citation can link straight to it.
 */
export function EvidenceCards({ evidence, deciding = [] }: { evidence: ToolCallRecord[]; deciding?: ToolName[] }) {
  const facts = parseEvidence(evidence);
  const rank = (f: Fact) => deciding.indexOf(f.record.tool_name as ToolName);
  const primary = facts.filter((f) => rank(f) >= 0).sort((a, b) => rank(a) - rank(b));
  const rest = facts.filter((f) => rank(f) < 0);
  if (facts.length === 0) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">No evidence was retrieved.</p>;
  }
  return (
    <div className="space-y-6">
      {primary.length > 0 ? (
        <>
          <Group label="What decides this case" facts={primary} all={facts} />
          <Group label="Other evidence reviewed" facts={rest} all={facts} />
        </>
      ) : (
        <Group label="Evidence gathered" facts={rest} all={facts} />
      )}
    </div>
  );
}
