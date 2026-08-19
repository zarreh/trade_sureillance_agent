import type { ComplianceFinding } from "@/lib/schemas";

export function ValidatorStrip({ finding }: { finding: ComplianceFinding }) {
  const report = finding.grounding_report;

  if (!report) {
    return (
      <p
        role="status"
        className="rounded bg-neutral-100 p-2 text-xs text-neutral-600 dark:bg-neutral-900 dark:text-neutral-400"
      >
        No grounding pass completed — this investigation stopped before drafting was judged.
      </p>
    );
  }

  const supported = report.claims.length - report.unsupported;
  return (
    <div
      role="status"
      className={`rounded p-2 text-xs ${
        report.unsupported === 0
          ? "bg-green-50 text-green-800 dark:bg-green-950 dark:text-green-200"
          : "bg-amber-50 text-amber-900 dark:bg-amber-950 dark:text-amber-200"
      }`}
    >
      Grounding: {supported}/{report.claims.length} claims supported, confidence:{" "}
      {report.confidence}
      {report.unsupported > 0 && ` — ${report.unsupported} unsupported`}
    </div>
  );
}
