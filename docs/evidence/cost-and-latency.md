# Cost and latency

!!! info "In one paragraph, for a non-engineer"
    Every investigation has a real cost and a real time-to-answer, and both
    are tracked per run rather than estimated after the fact.

`graph/cost_tracking.py`'s `CostTrackingHandler` attributes every LLM call's
tokens and estimated cost to the LangGraph node that made it, using each
call's `langgraph_node` run metadata — no manual threading through node code.
`RunStore` (`store/run_store.py`) persists this per real API investigation
run; the chart below instead comes from the Layer 1 canonical eval run
(`evals/canonical.py`), the only run this environment can generate on demand.

<figure markdown>
![Latency per investigation](../assets/cost-and-latency-per-investigation-light.svg#only-light)
![Latency per investigation](../assets/cost-and-latency-per-investigation-dark.svg#only-dark)
<figcaption markdown>Per-node latency, Layer 1 canonical run</figcaption>
</figure>

**Cost is $0 for every canonical scenario** — an honest consequence of
Layer 1 using `evals/oracle.py`'s deterministic chains rather than a live
model in this environment (see [Evaluation](evaluation.md)), not a
placeholder. The cost-tracking arithmetic itself is exercised directly
against real `LLMResult` payloads in `tests/graph/test_cost_tracking.py`, and
will show real per-node dollar figures the first time `POST /investigations`
runs against a live model with `SURVEILLANCE_OPENAI_API_KEY` set — visible
via `GET /investigations/{id}` and the UI cost meter (Phase 6).

Latency here is real: each canonical investigation's full graph run —
planning, tool calls against the real SQLite stores, the grounding loop —
timed end to end, p50/p95 computed the same way `evals/metrics.py` would for
a live-model Layer 1 or Layer 2 run.
