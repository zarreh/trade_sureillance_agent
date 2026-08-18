"use client";

import { useState } from "react";

type SkeletonEvent = {
  node: string;
  output: unknown;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export default function Home() {
  const [events, setEvents] = useState<SkeletonEvent[]>([]);
  const [running, setRunning] = useState(false);

  function runSkeleton() {
    setEvents([]);
    setRunning(true);
    const source = new EventSource(
      `${API_BASE}/investigations/skeleton/events?message=hello-from-nextjs`
    );
    source.onmessage = (event) => {
      const parsed = JSON.parse(event.data) as SkeletonEvent;
      setEvents((prev) => [...prev, parsed]);
      if (parsed.node === "__end__") {
        source.close();
        setRunning(false);
      }
    };
    source.onerror = () => {
      source.close();
      setRunning(false);
    };
  }

  return (
    <main className="mx-auto max-w-2xl p-8 font-sans">
      <h1 className="text-2xl font-bold">Trade Surveillance Agent</h1>
      <p className="mt-2 text-sm text-neutral-500">
        Phase 0 walking skeleton — streams the trivial{" "}
        <code>echo → done</code> graph node-by-node over SSE. Synthetic data
        only; not a supervisory system of record.
      </p>

      <button
        onClick={runSkeleton}
        disabled={running}
        className="mt-6 rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
      >
        {running ? "Running…" : "Run skeleton investigation"}
      </button>

      <ol className="mt-6 space-y-2">
        {events.map((event, i) => (
          <li key={i} className="rounded border border-neutral-200 p-3 text-sm">
            <span className="font-mono font-semibold">{event.node}</span>
            <pre className="mt-1 overflow-x-auto text-xs text-neutral-600">
              {JSON.stringify(event.output, null, 2)}
            </pre>
          </li>
        ))}
      </ol>
    </main>
  );
}

