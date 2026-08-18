# Tools

!!! info "In one paragraph, for a non-engineer"
    The agent cannot invent facts. It can only call one of six fixed,
    deterministic lookups against real data — every answer it gives has to
    trace back to one of these calls.

Six tools, each wrapping a single, parameterised query — the agent cannot
construct arbitrary SQL, and every tool result is addressable evidence the
grounding judge can cite (see [Grounding](../how-it-works/grounding.md)).

| Tool | Purpose | Backing store |
|---|---|---|
| `get_transaction_details` | Every transaction line reported in one filing, plus filing/insider context | `FactStore` |
| `get_applicable_role_limits` | The synthetic firm-policy limits that *apply* to a relationship/title — never asserts authorisation | `PolicyStore` |
| `get_compliance_rules` | The full severity-tiered rule table | `PolicyStore` |
| `rolling_90d_trading_volume` | An insider's trading volume in a rolling 90-day window ending at a given date, by transaction code | `FactStore` |
| `insider_trading_baseline` | An insider's own trailing transaction-value distribution, anchored to a given date | `FactStore` |
| `get_material_events` | Whether a date falls inside a seeded corporate-event blackout window | `PolicyStore` |

## Design decisions carried from docs/PLAN.md §3–§4

- **`get_transaction_details` returns every line in the filing, not one row.**
  A single accession can report a tax-withholding line and a sale together;
  returning only one would make it impossible for the grounding judge to catch
  an exemption bleeding from one line onto another (canonical scenario 7).
- **Every lookback is anchored to an explicit `as_of_date`, never `now()`.**
  The source notebook compared against the current wall-clock time while
  investigating a fixed historical window, making its own lookback
  meaningless.
- **One store connection per process, injected via a factory
  (`tools/registry.py`), not reopened per call.** `build_tools(fact_store,
  policy_store)` returns all six tools bound to shared store instances.
- **Naming does not overclaim.** `get_applicable_role_limits`, not
  `get_insider_authorization` — see [What it won't do](../how-it-works/what-it-wont-do.md).

Tested with no LLM and no network — see `tests/tools/`.
