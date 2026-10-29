import { ArrowRight, Search } from "lucide-react";
import Link from "next/link";
import { Suspense } from "react";

import { HowItWorks } from "@/components/HowItWorks";
import { RunConsole } from "@/components/RunConsole";
import { PageHeader } from "@/components/ui/PageHeader";
import { docsLink } from "@/lib/docs";

export default function Home() {
  return (
    <div className="space-y-10">
      <PageHeader
        icon={Search}
        eyebrow="Insider-trading surveillance"
        title="Does this insider trade need a second look?"
        docsHref={docsLink("plainLanguage")}
        docsLabel="Read how it works in plain language"
      >
        <p>
          Give it a Form 4 filing. It gathers evidence, drafts a conclusion, checks every claim
          against that evidence, and only then publishes: clear, flag or escalate. Its own process
          is audited in code, so a shortcut shows up.
        </p>
        <p>
          <Link
            className="inline-flex items-center gap-1 font-medium text-sky-700 hover:text-sky-900 dark:text-sky-400 dark:hover:text-sky-300"
            href="/evaluation"
          >
            How we know it isn&apos;t cutting corners
            <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
        </p>
      </PageHeader>

      <HowItWorks />

      <Suspense fallback={null}>
        <RunConsole />
      </Suspense>
    </div>
  );
}
