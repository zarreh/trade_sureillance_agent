"use client";

import { Gavel } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge, DispositionBadge } from "@/components/ui/Badge";
import { Callout } from "@/components/ui/Callout";
import { Card, CardTitle } from "@/components/ui/Card";
import { ApiError, getCase, putDecision, type CaseRow } from "@/lib/api";

type Disposition = "clear" | "flag" | "escalate";

const FIELD = "mt-1 block w-full rounded-md border border-line bg-surface px-3 py-2 text-sm text-fg";

/** Accept or override one completed run. Record-only: the finding above never changes. */
export function AnalystDecisionCard({
  accessionNumber,
  runId,
  aiDisposition,
}: {
  accessionNumber: string;
  runId: string;
  aiDisposition: string;
}) {
  const [row, setRow] = useState<CaseRow | null>(null);
  const [overriding, setOverriding] = useState(false);
  const [override, setOverride] = useState<Disposition>("escalate");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCase(accessionNumber)
      .then(setRow)
      .catch(() => setError("Could not load the current decision."));
  }, [accessionNumber]);

  async function save(decision: "accept" | "override") {
    setSaving(true);
    setError(null);
    try {
      const updated = await putDecision(accessionNumber, {
        run_id: runId,
        decision,
        override_disposition: decision === "override" ? override : null,
        note,
      });
      setRow(updated);
      setOverriding(false);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not save the decision.");
    } finally {
      setSaving(false);
    }
  }

  const current = row?.decision;
  const onThisRun = current?.run_id === runId;

  return (
    <Card aria-label="Analyst decision" className="space-y-4">
      <CardTitle icon={<Gavel className="h-4 w-4" aria-hidden />}>Analyst decision</CardTitle>
      <p className="text-sm text-muted">
        The AI suggests <DispositionBadge disposition={aiDisposition} />. Your decision is recorded against this
        run and never changes the finding.
      </p>

      {current && (
        <p role="status" className="flex flex-wrap items-center gap-2 text-sm text-fg">
          Recorded:
          <Badge variant={current.decision === "accept" ? "green" : "accent"}>
            {current.decision === "accept" ? "Accepted" : "Overridden"}
          </Badge>
          {current.override_disposition && <DispositionBadge disposition={current.override_disposition} />}
          {!onThisRun && <Badge variant="orange">Made on another run</Badge>}
          {current.note && <span className="text-muted">“{current.note}”</span>}
        </p>
      )}

      <label className="block text-sm font-medium text-fg">
        Note (optional)
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          maxLength={2000}
          rows={2}
          className={FIELD}
        />
      </label>

      {overriding && (
        <label className="block text-sm font-medium text-fg">
          Your disposition
          <select
            value={override}
            onChange={(e) => setOverride(e.target.value as Disposition)}
            className={FIELD}
          >
            <option value="clear">Clear</option>
            <option value="flag">Flag for review</option>
            <option value="escalate">Escalate</option>
          </select>
        </label>
      )}

      <div className="flex flex-wrap gap-2">
        {!overriding ? (
          <>
            <button
              type="button"
              disabled={saving}
              onClick={() => void save("accept")}
              className="rounded-lg bg-accent-400 px-4 py-2 text-sm font-medium text-accent-fg hover:bg-accent-300 disabled:opacity-50"
            >
              Accept AI suggestion
            </button>
            <button
              type="button"
              disabled={saving}
              onClick={() => setOverriding(true)}
              className="rounded-lg border border-line px-4 py-2 text-sm font-medium text-fg hover:border-accent-500 disabled:opacity-50"
            >
              Override…
            </button>
          </>
        ) : (
          <>
            <button
              type="button"
              disabled={saving}
              onClick={() => void save("override")}
              className="rounded-lg bg-accent-400 px-4 py-2 text-sm font-medium text-accent-fg hover:bg-accent-300 disabled:opacity-50"
            >
              Save override
            </button>
            <button
              type="button"
              onClick={() => setOverriding(false)}
              className="rounded-lg px-4 py-2 text-sm font-medium text-muted hover:text-fg"
            >
              Cancel
            </button>
          </>
        )}
      </div>

      {error && (
        <Callout variant="error" role="alert">
          {error}
        </Callout>
      )}
    </Card>
  );
}
