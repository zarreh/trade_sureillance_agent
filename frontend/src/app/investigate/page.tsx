import { Search } from "lucide-react";
import { Suspense } from "react";

import { RunConsole } from "@/components/RunConsole";
import { PageHeader } from "@/components/ui/PageHeader";
import { scenarioOptions } from "@/lib/case-data";
import { docsLink } from "@/lib/docs";

export const metadata = { title: "Investigate a filing · Trade Surveillance Agent" };

export default function InvestigatePage() {
  const samples = scenarioOptions();
  return (
    <div className="space-y-8">
      <PageHeader
        icon={Search}
        eyebrow="Live investigation"
        title="Investigate a filing"
        docsHref={docsLink("theInvestigation")}
        docsLabel="Read how an investigation works"
      >
        <p>
          Run the AI investigator on a filing in the loaded dataset and watch it work step by step. It uses the
          server&apos;s model credits. To see finished investigations without waiting, open one of the sample cases.
        </p>
      </PageHeader>
      <Suspense fallback={null}>
        <RunConsole samples={samples} />
      </Suspense>
    </div>
  );
}
