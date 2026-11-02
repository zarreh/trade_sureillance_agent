import { ListChecks } from "lucide-react";

import { CaseQueue } from "@/components/CaseQueue";
import { Callout } from "@/components/ui/Callout";
import { PageHeader } from "@/components/ui/PageHeader";

export const metadata = { title: "Case queue · Trade Surveillance Agent" };

export default function QueuePage() {
  return (
    <div className="space-y-6">
      <PageHeader icon={ListChecks} eyebrow="Analyst review" title="Case queue">
        <p>
          The ten synthetic sample filings plus every filing that has been investigated, each with the
          AI&apos;s latest suggestion and its process-audit score. Open a run to accept or override it.
        </p>
      </PageHeader>
      <Callout variant="info" title="AI suggestion. The analyst decides.">
        A decision is recorded against the run it was made on and never changes the AI finding. If a newer run
        finishes, the decision is marked stale.
      </Callout>
      <CaseQueue />
    </div>
  );
}
