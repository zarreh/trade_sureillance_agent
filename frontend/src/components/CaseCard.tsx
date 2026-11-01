import Link from "next/link";

import { Badge, DispositionBadge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { latest } from "@/lib/evidence";
import type { SampleCase } from "@/lib/case-data";

/** One entry in the sample-case list: the trade in a line, plus the answer key and the AI's result. */
export function CaseCard({ item }: { item: SampleCase }) {
  const { copy, data, facts, number } = item;
  const live = data.live;
  return (
    <Link
      href={`/cases/${copy.slug}`}
      className="block h-full rounded-xl focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500"
    >
      <Card className="h-full space-y-3 transition-colors hover:border-accent-400 dark:hover:border-accent-600">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Case {number}
        </p>
        <h3 className="text-base font-semibold text-slate-900 dark:text-white">{copy.title}</h3>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          {latest(facts, "details") ? copy.headline(facts) : data.name}
        </p>
        <dl className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-slate-600 dark:text-slate-300">
          <div className="flex items-center gap-1.5">
            <dt>Answer key</dt>
            <dd>
              <DispositionBadge disposition={data.expected_disposition} />
            </dd>
          </div>
          {live?.submitted && (
            <div className="flex items-center gap-1.5">
              <dt>AI run</dt>
              <dd className="flex items-center gap-1.5">
                <DispositionBadge disposition={live.submitted} />
                {live.correct === false && <Badge variant="red">Differs</Badge>}
              </dd>
            </div>
          )}
        </dl>
      </Card>
    </Link>
  );
}
