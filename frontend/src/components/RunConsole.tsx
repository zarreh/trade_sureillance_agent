"use client";

import { useEffect, useRef, useState } from "react";
import {
  createInvestigation,
  getInvestigation,
  streamInvestigationEvents,
  type InvestigationResponse,
} from "@/lib/api";
import { ComplianceFindingSchema, type TraceEvent } from "@/lib/schemas";
import { TraceTimeline } from "./TraceTimeline";
import { EvidencePanel } from "./EvidencePanel";
import { CostMeter } from "./CostMeter";
import { ValidatorStrip } from "./ValidatorStrip";

type Phase = "loading" | "streaming" | "success" | "empty" | "error";

// First paint first (docs/PLAN.md §7 Phase 6): a visitor watches a real
// investigation stream without typing anything. Scenario 1 is a good default
// — it's flagged, not trivially clear, so there's something to look at.
const DEFAULT_ACCESSION = "SCENARIO-0000000001-25-000001";

export function RunConsole({ accessionNumber = DEFAULT_ACCESSION }: { accessionNumber?: string }) {
  const [phase, setPhase] = useState<Phase>("loading");
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [investigation, setInvestigation] = useState<InvestigationResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const cleanupRef = useRef<() => void>(() => {});

  useEffect(() => {
    let cancelled = false;

    async function finish(id: string) {
      try {
        const result = await getInvestigation(id);
        if (cancelled) return;
        setInvestigation(result);
        if (result.status === "failed") {
          setPhase("error");
          setErrorMessage(result.error ?? "The investigation failed.");
        } else if (!result.finding) {
          setPhase("empty");
        } else {
          setPhase("success");
        }
      } catch {
        if (!cancelled) {
          setPhase("error");
          setErrorMessage("Could not fetch the finished investigation.");
        }
      }
    }

    async function start() {
      setPhase("loading");
      setEvents([]);
      setInvestigation(null);
      setErrorMessage(null);
      try {
        const created = await createInvestigation(accessionNumber);
        if (cancelled) return;
        setPhase("streaming");
        cleanupRef.current = streamInvestigationEvents(created.id, {
          onEvent: (event) => {
            if (cancelled) return;
            setEvents((prev) => [...prev, event]);
          },
          onEnd: () => {
            if (cancelled) return;
            void finish(created.id);
          },
          onError: () => {
            if (cancelled) return;
            setPhase("error");
            setErrorMessage("Lost connection to the investigation stream.");
          },
        });
      } catch {
        if (!cancelled) {
          setPhase("error");
          setErrorMessage("Could not start the investigation.");
        }
      }
    }

    void start();
    return () => {
      cancelled = true;
      cleanupRef.current();
    };
  }, [accessionNumber]);

  const parsedFinding =
    investigation?.finding != null
      ? ComplianceFindingSchema.safeParse(investigation.finding)
      : null;

  return (
    <div className="space-y-6">
      <p className="text-xs text-neutral-500">
        Synthetic data only — every accession here is a seeded canonical scenario, not a real
        filing.
      </p>

      {phase === "loading" && (
        <p role="status" className="text-sm text-neutral-500">
          Starting the investigation…
        </p>
      )}

      {phase === "error" && (
        <p
          role="alert"
          className="rounded bg-red-50 p-3 text-sm text-red-800 dark:bg-red-950 dark:text-red-200"
        >
          {errorMessage}
        </p>
      )}

      {phase === "empty" && (
        <p
          role="status"
          className="rounded bg-neutral-100 p-3 text-sm text-neutral-600 dark:bg-neutral-900 dark:text-neutral-400"
        >
          The investigation finished but produced no finding.
        </p>
      )}

      {(phase === "streaming" || phase === "success" || phase === "empty") && (
        <TraceTimeline events={events} />
      )}

      {phase === "success" && parsedFinding?.success && (
        <>
          <ValidatorStrip finding={parsedFinding.data} />
          <EvidencePanel finding={parsedFinding.data} />
        </>
      )}

      {investigation && (phase === "success" || phase === "empty") && (
        <CostMeter investigation={investigation} />
      )}
    </div>
  );
}
