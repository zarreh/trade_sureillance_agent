# D-A2-1: Publication is deterministic

**Status:** Accepted, implemented (`graph/nodes/publish.py`, Phase 4).

## Context

An earlier design ran `judge_grounding → finalizer`, where the finalizer was
a second LLM call that wrote the finding a user actually sees. Grounding
checked the *draft*, but a fresh model call wrote the *published* text
afterward — meaning a passing grounding check said nothing about the words
that ultimately got published. An unsupported claim could be reintroduced
after the check that was supposed to catch it. That defeats the point of
grounding at all.

## Decision

The draft is the artifact under judgement, and publication is a plain
function, not a model call:

```
draft_finding (LLM) → extract_claims (LLM, decomposes the draft's own text)
                    → judge_grounding (LLM, scores each claim)
                    → publish (no model call)
```

`publish` builds `PublishedFinding` from the judged draft's own
`model_dump()` plus the grounding report — it cannot alter `finding_text`
because it never sees a prompt. A test
(`tests/graph/test_publish.py::test_publish_is_byte_identical_to_the_judged_draft`,
plus the end-to-end version in
`tests/graph/test_surveillance_graph_integration.py`) asserts
`published.finding_text == draft_finding.finding_text` on every CI run.

## Consequences

- The published finding is provably the same text that was judged — not
  regenerated, not summarized, not re-worded.
- On a grounding failure, the *entire draft* is discarded and the
  investigation returns to `investigate` with specific unsupported-claim
  feedback (docs/PLAN.md §5.1) — there is no path to "patch" a bad draft
  into a passing one without re-investigating.
- One fewer LLM call per investigation than the rejected design (no
  finalizer), which also lowers cost and latency.
