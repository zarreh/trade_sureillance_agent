import { OwnerBadge, type Owner } from "@/components/ui/Badge";
import type { TraceEvent } from "@/lib/schemas";

const STEPS: Record<string, { label: string; owner: Owner }> = {
  plan: { label: "Planning the investigation", owner: "ai" },
  check_plan: { label: "Checking the plan is complete", owner: "code" },
  replan: { label: "Revising an incomplete plan", owner: "ai" },
  investigate: { label: "Investigator reasoning", owner: "ai" },
  tools: { label: "Running read-only tools against the real stores", owner: "code" },
  draft_finding: { label: "Drafting a conclusion", owner: "ai" },
  extract_claims: { label: "Decomposing the draft into claims", owner: "ai" },
  judge_grounding: { label: "Checking each claim against the evidence", owner: "both" },
  publish: { label: "Publishing the finding and auditing the process", owner: "code" },
  budget_exceeded: { label: "Stopped by the cost guardrail", owner: "code" },
};

export function TraceTimeline({ events }: { events: TraceEvent[] | { node: string }[] }) {
  // __end__ is a stream-termination marker, not an investigation step.
  const steps = events.filter((event) => event.node !== "__end__");
  if (steps.length === 0) {
    return <p className="text-sm text-muted">Waiting for the first step…</p>;
  }
  return (
    <ol className="space-y-2" aria-label="Investigation trace">
      {steps.map((event, i) => {
        const step = STEPS[event.node];
        return (
          <li
            key={i}
            className="flex items-center gap-3 rounded-lg border border-line bg-surface p-3 text-sm"
          >
            <span className="w-6 text-right font-mono text-xs text-muted">{i + 1}</span>
            <div className="min-w-0 flex-1">
              <div className="font-medium text-fg">
                {step?.label ?? event.node}
              </div>
              <div className="font-mono text-xs text-muted">{event.node}</div>
            </div>
            {step && <OwnerBadge owner={step.owner} />}
          </li>
        );
      })}
    </ol>
  );
}
