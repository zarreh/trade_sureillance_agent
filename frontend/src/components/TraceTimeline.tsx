import type { TraceEvent } from "@/lib/schemas";

const NODE_LABELS: Record<string, string> = {
  plan: "Planning the investigation",
  check_plan: "Checking the plan is complete",
  replan: "Revising an incomplete plan",
  investigate: "Investigator reasoning",
  tools: "Running tools against the real stores",
  draft_finding: "Drafting a conclusion",
  extract_claims: "Decomposing the draft into claims",
  judge_grounding: "Checking each claim against the evidence",
  publish: "Publishing the finding",
  budget_exceeded: "Stopped by the cost guardrail",
};

export function TraceTimeline({ events }: { events: TraceEvent[] }) {
  if (events.length === 0) {
    return <p className="text-sm text-neutral-500">Waiting for the first step…</p>;
  }
  return (
    <ol className="space-y-2" aria-label="Investigation trace">
      {events.map((event, i) => (
        <li
          key={i}
          className="flex items-baseline gap-3 rounded border border-neutral-200 p-3 text-sm dark:border-neutral-800"
        >
          <span className="font-mono text-xs text-neutral-400">{i + 1}</span>
          <div>
            <div className="font-semibold">{NODE_LABELS[event.node] ?? event.node}</div>
            <div className="font-mono text-xs text-neutral-500">{event.node}</div>
          </div>
        </li>
      ))}
    </ol>
  );
}
