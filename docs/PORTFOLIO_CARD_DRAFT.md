# Portfolio card (draft — staged for the shared portfolio site)

This is drafted content for the per-app card described in
`PORTFOLIO_PLAN_V3.md` §14. It lives here, excluded from this repo's own
published docs site (`mkdocs.yml` `exclude_docs`), because the shared
portfolio site (`/methodology`, `/writing`, the per-app card grid) does not
exist yet in this workspace — this file exists so the content is ready to
migrate once it does.

---

**Trade Surveillance Agent (A2)**

1. **Problem statement.** Executives, directors, and large shareholders have
   to publicly report their own trades within two business days — this
   agent investigates those filings for the patterns a human compliance
   reviewer would flag, and refuses to publish a conclusion it can't back
   with real evidence.
2. **Pillar badge.** Grounded reasoning / agentic evaluation.
3. **Live demo link.** *(pending deployment — see `docs/run-it-yourself.md`
   to run it locally in the meantime)*
4. **Live ops badge.** Not yet populated — requires a deployed instance with
   real traffic (X1). See [Cost and latency](../evidence/cost-and-latency.md)
   for the Layer 1 canonical-run figures available today.
5. **Architecture diagram.** See [Architecture overview](../architecture/overview.md).
6. **The artifact — the one thing to click.** The investigation replay: land
   on the page, watch a real filing get investigated node-by-node, see the
   grounding check run before the conclusion appears, click through to the
   rules cited and the exculpatory factors behind it.
7. **Stack badges.** FastAPI · LangGraph · Next.js · SQLite · pytest ·
   mypy --strict · Playwright · MkDocs Material.
8. **Key design decisions** (linked to this repo's ADRs):
   - [D-A2-1](../architecture/decisions/D-A2-1-deterministic-publication.md) — publication is deterministic, never re-generated after grounding passes.
   - [D-A2-5](../architecture/decisions/D-A2-5-vocabulary-discipline.md) — the vocabulary does not overclaim what the evidence supports.
   - [D-A2-6](../architecture/decisions/D-A2-6-two-evaluation-layers.md) — a canonical set gates every PR; nothing is published without stating *n*.
9. **Regulatory-basis link.** [regulatory-basis.md](../regulatory-basis.md).
10. **Repo link.** `github.com/zarreh/trade_sureillance_agent`.
11. **CTA.** *"This pattern, applied to your domain — let's talk."*
