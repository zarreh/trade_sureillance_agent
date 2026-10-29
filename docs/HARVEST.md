# Readiness review and extraction debt

Findings from the deployment-readiness checklist in
`cohort_risk_lab/UI-ENHANCEMENT-GUIDE.md` (Part A), run against this repository
on 2026-10-29, ranked by severity, with what was done about each.

## Findings

| Severity | Finding | Status |
|---|---|---|
| High | `POST /investigations` returned 202 for an accession that is not in `facts.db`; the run then failed in a background task. | Fixed: the route looks the accession up first and returns `404` with an actionable `detail`, creating no run. The UI shows the message. |
| High | The API had no CORS policy, so a browser page on `localhost:3000` calling the API on `:8000` was blocked. | Fixed: `SURVEILLANCE_FRONTEND_ORIGINS` allow-list; development also trusts any localhost port, other environments do not. |
| High | No production compose file, frontend image, `.dockerignore` or deployment guide. | Added `compose.prod.yaml`, `frontend/Dockerfile` (standalone Next.js build, non-root, health check), both `.dockerignore` files and [Deploy to a server](deploy.md). Images not yet built here (no Docker in the authoring environment). |
| Medium | The API image did not trust the proxy's `X-Forwarded-For`, so the per-client rate limit would have seen one address, the proxy's, for every visitor. | Fixed: `--proxy-headers --forwarded-allow-ips "*"`, safe only because no host port is published and the proxy overwrites the header (documented in the deploy guide). |
| Medium | A run in flight at a restart stayed `running` forever. | Fixed: on startup the API marks such runs `failed` ("interrupted by a server restart"). |
| Medium | No authentication, and every investigation spends model credits. | Not fixed in the app by design; the deploy guide puts basic auth at the proxy. The rate limit is a backstop. |
| Low | Two POSTs for the same accession start two independent runs. | Accepted. Runs are replayable records, the rate limit bounds the cost, and the run id (not the accession) is the key. An atomic claim would only matter if a run mutated shared state. |
| Low | `docs/PLAN.md` refers to `docs/regulatory_basis.md`; the file is `docs/regulatory-basis.md`. | Noted. |
| Low | `docs/PLAN.md` §11 says every chart regenerates byte-identically, but CI has no such check and the SVGs embed run-specific data (latency, metadata), so regenerating them changes the files. | Open. Only the RL results JSON, which is deterministic, has a CI drift check. |
| Low | The API's `finding` field is opaque JSON in the OpenAPI document, so generated types do not describe it. | Accepted. `frontend/src/lib/schemas.ts` validates it at runtime and is the frontend's source of truth. |

## Found by the live run

| Severity | Finding |
|---|---|
| High | Every real investigation through the API failed: LangGraph's default recursion limit of 25 is below a real run's length (about two steps per tool call, plus two evidence passes). Tests passed because the eval harness set its own limit of 100 and the API tests use fake chains. | Fixed: the run executor injects a limit of 100 (`WithRecursionLimit`; `astream_events` ignores a limit bound with `with_config`). Confirmed with one live run in a browser: it completed, and a reload replayed it with no console errors. |
| Medium | With real models the claim extractor cited no tool-call ids in 5 of 10 runs (provider ids such as `call_...` are long and opaque), so those findings scored 0 on the process audit's citation check. The audit worked as designed; the extractor is the weak point. Candidate fix: give the extractor short ids (`t1`, `t2`, ...) that map back to the real ones. |
| Medium | After the two evidence passes, findings are published even when the judge still marks claims unsupported (1 to 5 per run here). The count is shown, but a reader can miss it. Candidate fix: label such findings as partially grounded in the UI. |

## Failure visibility

A background failure reaches the UI as a run `error`: `RunConsole` renders the
stored `error` when a run ends `failed`, and the API now also fails runs cut off
by a restart instead of leaving them `running`.

## Extraction debt

The `components/ui/` primitives are copied from `clinical_care_navigator` rather
than shared, which makes this the third copy of them. Extraction into a shared
`@zarreh/agent-ui` package is portfolio decision D20 (`PORTFOLIO_PLAN_V4.md` §15),
planned for after this app's UI phase.
