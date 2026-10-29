import { OwnerBadge, type Owner } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";

const STEPS: { title: string; body: string; owner: Owner }[] = [
  { title: "Plan", body: "Decides which evidence the filing needs.", owner: "ai" },
  { title: "Check the plan", body: "Confirms every required check is planned, in order.", owner: "code" },
  {
    title: "Investigate",
    body: "Calls read-only tools over real SEC filings and a seeded firm-policy database.",
    owner: "both",
  },
  { title: "Draft and extract claims", body: "Writes a conclusion and splits it into checkable claims.", owner: "ai" },
  {
    title: "Grounding check",
    body: "A judge scores each claim against the evidence; code does the totals.",
    owner: "both",
  },
  {
    title: "Publish and audit",
    body: "Publishes the exact judged draft, then audits how the investigation worked.",
    owner: "code",
  },
];

export function HowItWorks() {
  return (
    <section aria-label="How it works">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        How it works
      </h2>
      <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {STEPS.map((step, i) => (
          <li key={step.title}>
            <Card className="h-full space-y-2">
              <div className="flex items-center justify-between gap-2">
                <span className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-sky-600 text-xs text-white">
                    {i + 1}
                  </span>
                  {step.title}
                </span>
                <OwnerBadge owner={step.owner} />
              </div>
              <p className="text-sm text-slate-600 dark:text-slate-300">{step.body}</p>
            </Card>
          </li>
        ))}
      </ol>
    </section>
  );
}
