"use client";

import { ExternalLink, RotateCw } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { Badge, DispositionBadge } from "@/components/ui/Badge";
import { Callout } from "@/components/ui/Callout";
import { ApiError, createInvestigation, listCases, type CaseRow } from "@/lib/api";

type DecisionState = "pending" | "accepted" | "overridden" | "stale";

export function decisionState(row: CaseRow): DecisionState {
  if (!row.decision) return "pending";
  if (row.decision.stale) return "stale";
  return row.decision.decision === "accept" ? "accepted" : "overridden";
}

const DECISION_BADGE: Record<DecisionState, { label: string; variant: "slate" | "green" | "accent" | "orange" }> = {
  pending: { label: "Pending", variant: "slate" },
  accepted: { label: "Accepted", variant: "green" },
  overridden: { label: "Overridden", variant: "accent" },
  stale: { label: "Stale: newer run", variant: "orange" },
};

const SELECT =
  "rounded-md border border-line bg-surface px-2 py-1.5 text-sm text-fg focus-visible:outline-2";

const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export function CaseQueue() {
  const router = useRouter();
  const [rows, setRows] = useState<CaseRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [disposition, setDisposition] = useState("all");
  const [decision, setDecision] = useState("all");
  const [starting, setStarting] = useState<string | null>(null);

  useEffect(() => {
    listCases()
      .then((body) => setRows(body.cases))
      .catch(() => setError("Could not load the case queue. Is the API running?"));
  }, []);

  const visible = useMemo(
    () =>
      (rows ?? []).filter((row) => {
        const d = row.latest_run?.disposition ?? "none";
        if (disposition !== "all" && d !== disposition) return false;
        if (decision !== "all" && decisionState(row) !== decision) return false;
        return true;
      }),
    [rows, disposition, decision]
  );

  async function rerun(accession: string) {
    setStarting(accession);
    setError(null);
    try {
      const created = await createInvestigation(accession);
      router.push(`/investigate?run=${created.id}`);
    } catch (e) {
      setStarting(null);
      setError(e instanceof ApiError ? e.message : "Could not start the investigation.");
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-xs font-medium uppercase tracking-wider text-muted">
          AI suggestion
          <select
            aria-label="Filter by AI suggestion"
            value={disposition}
            onChange={(e) => setDisposition(e.target.value)}
            className={`mt-1 block ${SELECT}`}
          >
            <option value="all">All</option>
            <option value="escalate">Escalate</option>
            <option value="flag">Flag for review</option>
            <option value="clear">Clear</option>
            <option value="none">Not investigated</option>
          </select>
        </label>
        <label className="text-xs font-medium uppercase tracking-wider text-muted">
          Analyst decision
          <select
            aria-label="Filter by analyst decision"
            value={decision}
            onChange={(e) => setDecision(e.target.value)}
            className={`mt-1 block ${SELECT}`}
          >
            <option value="all">All</option>
            <option value="pending">Pending</option>
            <option value="accepted">Accepted</option>
            <option value="overridden">Overridden</option>
            <option value="stale">Stale</option>
          </select>
        </label>
        {rows && (
          <p className="ml-auto text-sm text-muted tabular" role="status">
            {visible.length} of {rows.length} cases
          </p>
        )}
      </div>

      {error && (
        <Callout variant="error" role="alert">
          {error}
        </Callout>
      )}
      {!rows && !error && (
        <p role="status" className="text-sm text-muted">
          Loading the case queue…
        </p>
      )}

      {rows && (
        <div className="overflow-x-auto rounded-lg border border-line bg-surface">
          <table className="w-full min-w-[60rem] text-left text-sm">
            <thead className="border-b border-line bg-surface-2 text-xs uppercase tracking-wider text-muted">
              <tr>
                <th scope="col" className="px-3 py-2 font-semibold">Accession</th>
                <th scope="col" className="px-3 py-2 font-semibold">Insider · issuer</th>
                <th scope="col" className="px-3 py-2 font-semibold">Trade</th>
                <th scope="col" className="px-3 py-2 text-right font-semibold">Value</th>
                <th scope="col" className="px-3 py-2 font-semibold">AI suggestion</th>
                <th scope="col" className="px-3 py-2 text-right font-semibold">Audit</th>
                <th scope="col" className="px-3 py-2 font-semibold">Analyst</th>
                <th scope="col" className="px-3 py-2 font-semibold">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {visible.map((row) => {
                const run = row.latest_run;
                const state = decisionState(row);
                return (
                  <tr key={row.accession_number} data-testid="case-row" className="hover:bg-surface-2">
                    <td className="whitespace-nowrap px-3 py-2 font-mono text-xs text-fg">
                      {row.accession_number}
                      {row.is_scenario && (
                        <div className="mt-1 font-sans">
                          <Badge variant="slate">Synthetic</Badge>
                        </div>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <div className="text-fg">{row.filing?.insider_name ?? "—"}</div>
                      <div className="text-xs text-muted">
                        {row.filing?.relationship ?? ""}
                        {row.filing ? ` · ${row.filing.issuer_name}` : ""}
                      </div>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 font-mono text-xs text-muted">
                      {row.filing ? `${row.filing.trade_date} · ${row.filing.transaction_codes.join("/")}` : "—"}
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-xs tabular text-fg">
                      {row.filing?.total_value != null ? usd.format(row.filing.total_value) : "—"}
                    </td>
                    <td className="px-3 py-2">
                      {run?.disposition ? (
                        <span className="flex flex-wrap items-center gap-1">
                          <DispositionBadge disposition={run.disposition} />
                          {run.severity && <span className="text-xs text-muted">{run.severity}</span>}
                        </span>
                      ) : run ? (
                        <Badge variant="slate">{run.status === "running" ? "Running…" : run.status}</Badge>
                      ) : (
                        <span className="text-xs text-muted">Not investigated</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-xs tabular">
                      {run?.trajectory_score != null ? (
                        <span
                          title="Process audit score: evidence gathered, ordering, real citations, supported exemptions"
                          className={run.trajectory_score < 0.5 ? "text-red-600 dark:text-red-400" : "text-fg"}
                        >
                          {run.trajectory_score.toFixed(2)}
                        </span>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <Badge variant={DECISION_BADGE[state].variant}>{DECISION_BADGE[state].label}</Badge>
                      {row.decision?.decision === "override" && row.decision.override_disposition && (
                        <span className="ml-1 text-xs text-muted">→ {row.decision.override_disposition}</span>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex justify-end gap-1">
                        {run && (
                          <Link
                            href={`/investigate?run=${run.id}`}
                            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-accent-700 hover:bg-surface-2 dark:text-accent-300"
                          >
                            <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                            Open
                          </Link>
                        )}
                        <button
                          type="button"
                          onClick={() => void rerun(row.accession_number)}
                          disabled={starting !== null}
                          aria-label={`${run ? "Re-run" : "Investigate"} ${row.accession_number}`}
                          className="inline-flex items-center gap-1 whitespace-nowrap rounded-md border border-line px-2 py-1 text-xs font-medium text-fg hover:border-accent-500 disabled:opacity-50"
                        >
                          <RotateCw className="h-3.5 w-3.5" aria-hidden />
                          {starting === row.accession_number ? "Starting…" : run ? "Re-run" : "Investigate"}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {visible.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-3 py-6 text-center text-sm text-muted">
                    No cases match these filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
