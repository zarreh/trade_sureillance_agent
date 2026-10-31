import { ArrowLeft } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { CaseOutcome } from "@/components/CaseOutcome";
import { CaseRunPanel } from "@/components/CaseRunPanel";
import { ViewTabs, type TabSpec } from "@/components/ViewTabs";
import { Callout } from "@/components/ui/Callout";
import { Card, CardTitle } from "@/components/ui/Card";
import { caseCopyBySlug } from "@/lib/cases";
import { sampleCase, sampleCases } from "@/lib/case-data";

type Params = { slug: string };

export const dynamicParams = false;

export function generateStaticParams(): Params[] {
  return sampleCases().map((c) => ({ slug: c.copy.slug }));
}

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const copy = caseCopyBySlug((await params).slug);
  return { title: copy ? `${copy.title} · Trade Surveillance Agent` : "Case · Trade Surveillance Agent" };
}

function Bullets({ items, empty }: { items: string[]; empty: string }) {
  if (items.length === 0) return <p className="text-sm text-slate-500 dark:text-slate-400">{empty}</p>;
  return (
    <ul className="list-disc space-y-2 pl-5 text-sm leading-relaxed text-slate-800 dark:text-slate-100">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

export default async function CasePage({ params }: { params: Promise<Params> }) {
  const item = sampleCase((await params).slug);
  if (!item) notFound();
  const { copy, data, facts, number } = item;
  const pair = copy.pairWith ? caseCopyBySlug(copy.pairWith) : undefined;

  const reference = (
    <CaseRunPanel
      kind="reference"
      finding={data.reference.finding}
      evidence={data.reference.evidence}
      deciding={copy.deciding}
      events={data.reference.events}
    />
  );
  const tabs: TabSpec[] = data.live
    ? [
        {
          id: "ai",
          label: "What the AI investigator did",
          content: (
            <CaseRunPanel
              kind="ai"
              finding={data.live.finding}
              evidence={data.live.evidence}
              deciding={copy.deciding}
            />
          ),
        },
        { id: "reference", label: "Reference investigation", content: reference },
      ]
    : [];

  return (
    <div className="space-y-8">
      <Link
        href="/"
        className="inline-flex items-center gap-1 text-sm font-medium text-sky-700 hover:underline dark:text-sky-300"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden />
        All sample cases
      </Link>

      <Callout variant="info" title="Sample case">
        A synthetic trade checked against synthetic firm policy. The people and the company are invented.
      </Callout>

      <header className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-wider text-sky-700 dark:text-sky-400">
          Case {number}: {copy.title}
        </p>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl dark:text-white">
          {copy.headline(facts)}
        </h1>
        <p className="max-w-3xl text-[15px] leading-relaxed text-slate-600 dark:text-slate-300">{copy.whyTricky}</p>
      </header>

      <div className="grid gap-3 md:grid-cols-2">
        <Card tone="amber" className="space-y-3">
          <CardTitle>Reasons for concern</CardTitle>
          <Bullets items={copy.concerns(facts)} empty="The evidence raised no specific concern." />
        </Card>
        <Card tone="emerald" className="space-y-3">
          <CardTitle>What could explain it</CardTitle>
          <Bullets items={copy.explanations(facts)} empty="Nothing in the filing offers an explanation." />
        </Card>
      </div>

      <CaseOutcome data={data} />

      {tabs.length > 0 ? <ViewTabs label="Which investigation to show" tabs={tabs} /> : reference}

      {pair && (
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Compare with{" "}
          <Link className="font-medium text-sky-700 underline dark:text-sky-300" href={`/cases/${pair.slug}`}>
            {pair.title}
          </Link>
          .
        </p>
      )}
    </div>
  );
}
