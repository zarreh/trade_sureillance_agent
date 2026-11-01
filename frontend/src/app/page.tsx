import { ArrowRight, Search } from "lucide-react";
import Link from "next/link";

import { CaseCard } from "@/components/CaseCard";
import { HowItWorks } from "@/components/HowItWorks";
import { SpotTheDifference, type QuizFiling } from "@/components/SpotTheDifference";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { FAILURE_MODES, tradeRows, type FailureMode } from "@/lib/cases";
import { liveSummary, sampleCases, type SampleCase } from "@/lib/case-data";
import { docsLink } from "@/lib/docs";

function toFiling(label: "A" | "B", item: SampleCase): QuizFiling {
  return {
    label,
    slug: item.copy.slug,
    title: item.copy.title,
    rows: tradeRows(item.facts),
    answerKey: item.data.expected_disposition,
    decisive: item.copy.explanations(item.facts)[0] ?? "",
  };
}

const FAILURE_ORDER: FailureMode[] = ["crying-wolf", "one-excuse", "unsupported"];

// Grouped by what a wrong answer costs: a missed alert, or a false alarm.
const CASE_GROUPS = [
  {
    title: "Worth an analyst's time",
    blurb: "Missing any of these is how a real violation slips through.",
    matches: (d: string) => d !== "clear",
  },
  {
    title: "Should not be alarms",
    blurb: "Flagging any of these is a false alarm, and false alarms are what bury analysts.",
    matches: (d: string) => d === "clear",
  },
];

export default function Home() {
  const cases = sampleCases();
  const planned = cases.find((c) => c.copy.slug === "planned-sale");
  const blackout = cases.find((c) => c.copy.slug === "blackout-sale");
  const live = blackout?.data.live ? liveSummary(blackout.data.live) : null;
  const liveNote =
    blackout && live?.unsupported
      ? `In the recorded live run on case ${blackout.number}, ${live.unsupported} of ${live.claimCount} claims were judged unsupported, and the result is marked for human review.`
      : null;

  return (
    <div className="space-y-12">
      <PageHeader
        icon={Search}
        eyebrow="Insider-trading surveillance"
        title="Which insider trades deserve an investigation?"
        docsHref={docsLink("plainLanguage")}
        docsLabel="Read how it works in plain language"
      >
        <p>
          Company insiders must publicly report their stock trades. Compliance teams watch those filings for the few
          that might be trading on secret information.
        </p>
        <p>
          Flag everything and analysts drown in false alarms. Clear too easily and a real violation slips through.
          This demo shows an AI investigator working through sample filings, and the checks that stand between its
          draft and a published conclusion.
        </p>
      </PageHeader>

      {planned && blackout && <SpotTheDifference filings={[toFiling("A", planned), toFiling("B", blackout)]} />}

      <section aria-label="Three ways surveillance goes wrong" className="space-y-4">
        <h2 className="text-xl font-semibold text-slate-900 dark:text-white">Three ways surveillance goes wrong</h2>
        <ul className="grid gap-3 md:grid-cols-3">
          {FAILURE_ORDER.map((mode) => {
            const item = FAILURE_MODES[mode];
            return (
              <li key={mode}>
                <Card className="flex h-full flex-col gap-3">
                  <h3 className="font-semibold text-slate-900 dark:text-white">{item.title}</h3>
                  <p className="text-sm text-slate-600 dark:text-slate-300">
                    {item.problem}
                    {mode === "unsupported" && liveNote ? ` ${liveNote}` : ""}
                  </p>
                  <p className="text-sm text-slate-800 dark:text-slate-100">
                    <span className="font-semibold">The safeguard: </span>
                    {item.safeguard}
                  </p>
                  <Link
                    href={`/cases/${item.caseSlug}`}
                    className="mt-auto inline-flex items-center gap-1 text-sm font-medium text-accent-700 hover:underline dark:text-accent-300"
                  >
                    See it in a case
                    <ArrowRight className="h-4 w-4" aria-hidden />
                  </Link>
                </Card>
              </li>
            );
          })}
        </ul>
      </section>

      <section aria-label="Sample cases" className="space-y-6">
        <div className="space-y-1">
          <h2 className="text-xl font-semibold text-slate-900 dark:text-white">Explore sample cases</h2>
          <p className="max-w-3xl text-sm text-slate-600 dark:text-slate-300">
            Each case is a synthetic filing with a known right answer. Open one to see the evidence, the
            investigator&apos;s conclusion, and what the safeguards said about it.
          </p>
        </div>
        {CASE_GROUPS.map((group) => {
          const items = cases.filter((c) => group.matches(c.data.expected_disposition));
          return (
            <div key={group.title} className="space-y-3">
              <div>
                <h3 className="font-semibold text-slate-900 dark:text-white">{group.title}</h3>
                <p className="text-sm text-slate-600 dark:text-slate-300">{group.blurb}</p>
              </div>
              <ul className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                {items.map((item) => (
                  <li key={item.copy.slug}>
                    <CaseCard item={item} />
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </section>

      <section aria-label="Under the hood" className="space-y-4">
        <h2 className="text-xl font-semibold text-slate-900 dark:text-white">Under the hood</h2>
        <HowItWorks />
        <p className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
          <Link
            className="inline-flex items-center gap-1 font-medium text-accent-700 hover:underline dark:text-accent-300"
            href="/evaluation"
          >
            How we know it isn&apos;t cutting corners
            <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
          <Link
            className="inline-flex items-center gap-1 font-medium text-accent-700 hover:underline dark:text-accent-300"
            href="/investigate"
          >
            Investigate a filing yourself
            <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
        </p>
      </section>
    </div>
  );
}
