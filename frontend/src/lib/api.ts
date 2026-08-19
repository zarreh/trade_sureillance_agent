import { TraceEventSchema, type TraceEvent } from "./schemas";
import type { components } from "./api-types";

export type CreateInvestigationResponse =
  components["schemas"]["CreateInvestigationResponse"];
export type InvestigationResponse = components["schemas"]["InvestigationResponse"];

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number
  ) {
    super(message);
  }
}

export async function createInvestigation(
  accessionNumber: string
): Promise<CreateInvestigationResponse> {
  const response = await fetch(`${API_BASE}/investigations`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ accession_number: accessionNumber }),
  });
  if (!response.ok) {
    throw new ApiError(`Failed to start investigation (${response.status})`, response.status);
  }
  return response.json() as Promise<CreateInvestigationResponse>;
}

export async function getInvestigation(id: string): Promise<InvestigationResponse> {
  const response = await fetch(`${API_BASE}/investigations/${id}`);
  if (!response.ok) {
    throw new ApiError(`Failed to fetch investigation (${response.status})`, response.status);
  }
  return response.json() as Promise<InvestigationResponse>;
}

export type TraceEventHandlers = {
  onEvent: (event: TraceEvent) => void;
  onEnd: () => void;
  onError: () => void;
};

/** Subscribes to GET /investigations/{id}/events (SSE). Returns a cleanup
 * function that closes the connection — call it on unmount. */
export function streamInvestigationEvents(id: string, handlers: TraceEventHandlers): () => void {
  const source = new EventSource(`${API_BASE}/investigations/${id}/events`);
  source.onmessage = (message) => {
    let parsed: unknown;
    try {
      parsed = JSON.parse(message.data as string);
    } catch {
      handlers.onError();
      return;
    }
    const result = TraceEventSchema.safeParse(parsed);
    if (!result.success) {
      handlers.onError();
      return;
    }
    handlers.onEvent(result.data);
    if (result.data.node === "__end__") {
      source.close();
      handlers.onEnd();
    }
  };
  source.onerror = () => {
    source.close();
    handlers.onError();
  };
  return () => source.close();
}
