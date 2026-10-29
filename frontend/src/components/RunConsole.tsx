"use client";

import { ArrowLeft, Play } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { InvestigationView } from "./InvestigationView";
import { Callout } from "@/components/ui/Callout";
import {
  ApiError,
  createInvestigation,
  getInvestigation,
  streamInvestigationEvents,
  type InvestigationResponse,
} from "@/lib/api";
import example from "@/generated/example-run.json";
import { ComplianceFindingSchema, ExampleRunSchema, type TraceEvent } from "@/lib/schemas";

type Phase = "idle" | "loading" | "streaming" | "success" | "empty" | "error";

const EXAMPLE = ExampleRunSchema.parse(example);

// Scenario 1 is flagged, not trivially clear, so there is something to look at.
const DEFAULT_ACCESSION = EXAMPLE.accession_number;

/**
 * First paint shows a recorded example for free. "Run it live" starts a real
 * investigation and puts its id in the URL (`?run=`), so a reload replays the
 * stored run from the API instead of starting another.
 */
export function RunConsole() {
  const router = useRouter();
  const runId = useSearchParams().get("run");
  const [accession, setAccession] = useState(DEFAULT_ACCESSION);
  const [phase, setPhase] = useState<Phase>("idle");
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [investigation, setInvestigation] = useState<InvestigationResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const cleanupRef = useRef<() => void>(() => {});

  useEffect(() => {
    if (!runId) {
      setPhase("idle");
      setEvents([]);
      setInvestigation(null);
      return;
    }
    let cancelled = false;
    setPhase("streaming");
    setEvents([]);
    setInvestigation(null);
    setErrorMessage(null);

    async function finish(id: string) {
      try {
        const result = await getInvestigation(id);
        if (cancelled) return;
        setInvestigation(result);
        if (result.status === "failed") {
          setPhase("error");
          setErrorMessage(result.error ?? "The investigation failed.");
        } else {
          setPhase(result.finding ? "success" : "empty");
        }
      } catch {
        if (!cancelled) {
          setPhase("error");
          setErrorMessage("Could not fetch the finished investigation.");
        }
      }
    }

    cleanupRef.current = streamInvestigationEvents(runId, {
      onEvent: (event) => {
        if (!cancelled) setEvents((prev) => [...prev, event]);
      },
      onEnd: () => {
        if (!cancelled) void finish(runId);
      },
      onError: () => {
        if (!cancelled) {
          setPhase("error");
          setErrorMessage("Lost connection to the investigation stream.");
        }
      },
    });
    return () => {
      cancelled = true;
      cleanupRef.current();
    };
  }, [runId]);

  async function runLive(event: React.FormEvent) {
    event.preventDefault();
    setPhase("loading");
    setErrorMessage(null);
    try {
      const created = await createInvestigation(accession.trim());
      router.replace(`/?run=${created.id}`);
    } catch (error) {
      setPhase("error");
      setErrorMessage(
        error instanceof ApiError ? error.message : "Could not start the investigation."
      );
    }
  }

  const parsedFinding =
    investigation?.finding != null ? ComplianceFindingSchema.safeParse(investigation.finding) : null;
  const busy = phase === "loading" || phase === "streaming";

  return (
    <div className="space-y-6">
      <form onSubmit={runLive} className="flex flex-wrap items-end gap-3">
        <label className="min-w-0 flex-1 text-sm font-medium text-slate-700 dark:text-slate-200">
          Accession number
          <input
            value={accession}
            onChange={(e) => setAccession(e.target.value)}
            className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
          />
        </label>
        <button
          type="submit"
          disabled={busy || accession.trim() === ""}
          className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-50"
        >
          <Play className="h-4 w-4" aria-hidden />
          Run it live
        </button>
        {runId && (
          <button
            type="button"
            onClick={() => router.replace("/")}
            className="inline-flex items-center gap-1 rounded-lg px-3 py-2 text-sm font-medium text-sky-700 hover:bg-sky-50 dark:text-sky-300 dark:hover:bg-sky-950"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden />
            Back to the example
          </button>
        )}
      </form>

      {phase === "idle" && (
        <>
          <Callout variant="info" title="Recorded example">
            Canonical scenario 1, replayed from a stored run. It used the scripted stand-in for the
            AI model, so it cost nothing and is not a measure of model quality. Running it live uses
            the server&apos;s model credits.
          </Callout>
          <InvestigationView
            events={EXAMPLE.events}
            finding={EXAMPLE.finding}
            investigation={null}
          />
        </>
      )}

      {phase === "loading" && (
        <p role="status" className="text-sm text-slate-500 dark:text-slate-400">
          Starting the investigation…
        </p>
      )}

      {phase === "error" && (
        <Callout variant="error" role="alert">
          {errorMessage}
        </Callout>
      )}

      {phase === "empty" && (
        <Callout variant="info" role="status">
          The investigation finished but produced no finding.
        </Callout>
      )}

      {(phase === "streaming" || phase === "success" || phase === "empty") && (
        <InvestigationView
          events={events}
          finding={phase === "success" && parsedFinding?.success ? parsedFinding.data : null}
          investigation={investigation && (phase === "success" || phase === "empty") ? investigation : null}
        />
      )}
    </div>
  );
}
