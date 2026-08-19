# D-A2-5: The vocabulary does not overclaim

**Status:** Accepted, implemented throughout `tools/`, `schemas/`, `graph/evidence.py`.

## Context

The source material this project's problem framing drew on used names that
assert more than the evidence supports: `get_insider_authorization` implies
a trade was cleared; "valid 10b5-1 plan" implies verification that never
happened; an exculpatory factor derived from one transaction line could
silently be read as clearing the whole filing.

## Decision

Every name and value in this codebase is scoped to exactly what the
evidence supports, nothing more:

- `get_applicable_role_limits`, not `get_insider_authorization` — this tool
  selects an *applicable* limit from a seeded policy table; it does not
  assert that any trade was authorized or pre-cleared
  (`tools/get_applicable_role_limits.py`).
- `reported_under_10b5_1`, not "valid 10b5-1 plan" — a tri-state
  (`true`/`false`/`unknown`) reflecting only whether the filing *reported*
  the indicator, never whether a plan was independently verified.
  `unknown` renders in the UI as "not established" — never as an absence of
  a plan (`frontend/src/components/EvidencePanel.tsx`).
- `ExculpatoryFactor.applies_to_transaction_sk` scopes every exemption to
  one transaction line, never a whole accession — a tax-withholding line's
  exemption must never be read as clearing an unrelated sale in the same
  filing (canonical scenario 7, `graph/evidence.py`).
- `pre_cleared` is deliberately absent from `ExculpatoryKind` — there is no
  approvals-workflow evidence anywhere in this system to support it.

## Consequences

- A reviewer reading a published finding cannot mistake a data-lookup
  result for a compliance conclusion the system doesn't have evidence for.
- Renaming cost nothing at build time (these are new names on a from-scratch
  implementation, not a rename of shipped code) but would be expensive to
  retrofit after a name had shipped and been relied upon.
- This discipline is enforced at the type level where possible
  (`ExculpatoryKind`'s `Literal` has no `pre_cleared` member to accidentally
  reach for) rather than by convention alone.
