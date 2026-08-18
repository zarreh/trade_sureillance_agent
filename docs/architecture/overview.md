# Architecture overview

!!! info "In one paragraph, for a non-engineer"
    The system is a small pipeline: plan the investigation, check the plan makes
    sense, gather evidence with a fixed set of tools, draft a conclusion, check
    that conclusion against the evidence, and only then show it to you.

```mermaid
graph TD
  plan[plan] --> check_plan{check_plan}
  check_plan -- replan, max 1 --> plan
  check_plan -- ok --> investigate[investigate + tools]
  investigate --> draft[draft_finding]
  draft --> extract[extract_claims]
  extract --> judge{judge_grounding}
  judge -- unsupported --> investigate
  judge -- supported --> publish[publish]
```

See [docs/PLAN.md](https://github.com/PLACEHOLDER/trade-surveillance-agent/blob/main/docs/PLAN.md)
§5 for the full design and the reasoning behind each decision. Architecture
decision records land in Phase 8; this page grows alongside the implementation
phases.
