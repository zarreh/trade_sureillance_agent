# D-A2-4: Fallback is for availability, not validation

**Status:** Partially implemented. Single-provider profile (OpenAI) ships in
base; the Gemini availability-fallback and Ollama offline profile described
below are designed but not yet built (`graph/policies.py` module docstring
tracks this explicitly).

## Context

A common but dangerous pattern is to catch *any* exception from a model call
and retry against a different provider. That silently papers over the exact
class of failure this app exists to surface — a schema-validation failure or
a tool-calling defect is a *real problem with the prompt or the model*, not
a transient availability issue, and hiding it behind an automatic fallback
means a broken investigation can look like a successful one.

## Decision

Fallback exists to handle *transport*-level failure only — connection
errors, timeouts, 429s, 5xxs — never to catch and retry past a schema or
tool-calling failure, which must surface as a real error. The planned
design: OpenAI as the primary provider; a Gemini equivalent engages only on
transport-level failure; an explicit `offline` profile (Ollama, selected by
a setting, not engaged automatically) for local development and a
data-sovereignty demo. `.with_structured_output()` must be bound per model
*before* composing any fallback wrapper — calling it on an
already-fallback-wrapped runnable does not behave correctly.

Base (Phases 3–7) ships **only** the OpenAI profile
(`build_fast_model`/`build_reasoning_model`, `graph/policies.py`). The
Gemini fallback and Ollama offline profile, and the cross-provider contract
tests that would run outside pull-request CI against the same Pydantic
schemas, are scheduled but not blocking the base build.

## Consequences

- Today: a transport failure surfaces as a run failure (`RunStore.fail_run`),
  not a silent retry — honest, if less resilient than the target design.
- When built: an outage of one provider doesn't take the whole app down, but
  a genuine schema or tool-calling defect still surfaces immediately rather
  than being masked by a fallback attempt.
- Deferring this was a deliberate scope decision, not an oversight — it does
  not block anything in the base build's exit criteria, and building it
  before the base pipeline was proven end to end would have been premature.
