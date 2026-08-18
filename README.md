# A2 — Trade Surveillance Agent

> Insider-trading surveillance that has to show its work.

Portfolio app **A2** (`PORTFOLIO_PLAN_V3.md` §7). Finance / RegTech, Pillar 1 —
Regulated Decision Automation. Target URL: `surveillance.zarreh.ai`.

Takes a securities transaction in SEC Form 4 shape and runs an investigation:
pulls the transaction record, checks insider authorisation and trading limits,
retrieves compliance rules with severity tiers, computes quarterly volume against
thresholds, compares against the insider's own historical baseline, and issues a
finding — **clear / flag / escalate** — where every assertion traces to a
retrieved fact.

The centrepiece is a **grounding validator that re-routes**: it re-reads the draft
finding and rejects any assertion unsupported by a tool result, sending the
investigation back for another evidence pass.

**Status:** planning. Nothing implemented yet — see [docs/PLAN.md](docs/PLAN.md).

This is a research prototype built on public SEC data plus synthetic firm policy.
It is **not** a supervisory system of record.

## Layout

| Path | Purpose |
|---|---|
| `docs/PLAN.md` | The build plan — phases, architecture, decisions, risks |
| `reference/` | Local-only source material. **Gitignored**, never published |

Everything else arrives in Phase 0.
