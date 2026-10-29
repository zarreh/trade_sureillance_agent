# D-A2-7: The process audit is the reward's trajectory component

**Status:** Accepted, implemented in `graph/trajectory_audit.py` and attached by
`graph/nodes/publish.py`.

## Context

The product checks the *plan* (`check_plan`) and, through an LLM judge, whether
each *claim* is supported. Nothing deterministic checks what the investigator
actually did: whether it gathered every required piece of evidence, started
with the transaction details, cited only tool calls that exist, or stated an
exemption the filing does not back.

## Decision

One pure function, `audit_trajectory`, inspects the tool-call records, the
claims and the claimed exemptions, and returns a `ProcessAudit`. It lives in
`src/` so the product and the later RL reward share a single implementation.

- `publish` attaches the audit to `PublishedFinding.process_audit`. It is
  **record-only**: it never changes the disposition, the text or the routing,
  so "published == judged draft" (D-A2-1) still holds.
- `below_all_thresholds` is never an exemption. Being under the dollar limits
  says nothing about a blackout or late-filing violation.
- An exemption naming a transaction must hold for that line; a tax-withholding
  `F` line does not support an exemption on an unrelated `S` line (canonical
  case 7).
- No claims scores `citation_validity = 0`, not a vacuous 1: nothing is
  traceable.
- Exemptions asserted in claim text are found with a keyword map. A clause
  containing a negation ("no 10b5-1 plan was reported", "status unknown") is
  skipped.

## Consequences

- Exculpatory factors are derived from tool results in code, so the structured
  field is valid by construction. The audit's value in the product is the
  narrative mention, the citation check and the coverage check.
- The negation rule under-detects rather than over-detects: a clause such as
  "although unproven, this was a 10b5-1 sale" is not caught. A false alarm on
  a correctly negated sentence was judged worse than a miss, because the audit
  is shown to reviewers.
- Budget-exceeded runs end at `budget_exceeded` without publishing, so they
  carry no audit.
