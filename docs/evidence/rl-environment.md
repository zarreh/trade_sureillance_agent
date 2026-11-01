# RL environment: can a shortcut score well?

!!! info "In one paragraph, for a non-engineer"
    The product investigates a trade and publishes a finding. This page asks a
    harder question: could an investigator that cuts corners still look good?
    To find out, the same investigation loop is turned into a small practice
    environment with a scoring rule, and a handful of scripted shortcut
    strategies are run through it. Each one scores far below a proper
    investigation, and a test in CI keeps it that way. It is an extra on top of
    the surveillance product, not the product itself.

## Problem

An insider-trading investigator can look right while cutting corners: skipping
evidence, citing things it never retrieved, or asserting a 10b5-1 exemption the
filing does not support. Wrong dispositions also have asymmetric costs: a
missed violation is worse than an extra alert, but alert fatigue is the real
price of over-flagging ([False positives](false-positives.md)).

Regulatory frame: SEC Rule 10b-5, Section 16(a), Rule 10b5-1 and FINRA 3110
(see [Regulatory basis](../regulatory-basis.md)).

## Verification

What is checked, and by what:

| Check | By | Where |
|---|---|---|
| The plan covers every mandatory tool, details first | Code | `check_plan` |
| Exculpatory factors come from tool results | Code | `graph/evidence.py` |
| Each claim is **supported** by the evidence | **An LLM judge** | `judge_grounding` |
| Evidence gathered, ordering, real citations, supported exemptions | Code | `graph/trajectory_audit.py` |
| The reward | Code, no LLM | `evals/rl_env.py` |

The process audit runs on every real investigation and is shown on the
finding, record-only ([D-A2-7](../architecture/decisions/D-A2-7-process-audit.md)).
The reward reuses the same function as its trajectory component
([D-A2-8](../architecture/decisions/D-A2-8-reward-design.md)).

## The environment

`SurveillanceEnv` is a Gymnasium environment. Observations and actions are JSON
strings, which is what an LLM policy would emit.

- `reset` returns the accession number, the tool list with argument schemas and
  the tool-call budget. It never returns a label, scenario id or name.
- `step` takes either a tool call (the real tool runs) or a `submit` with a
  disposition, claims that cite tool-call ids, and any exemptions claimed.
- Unparseable actions, unknown tools and bad arguments cost 0.05 and count
  toward the budget. Exceeding the budget ends the episode at -0.5.
- Only the six real tools run; the plan, judge and finding nodes do not.

## Results

| Policy | What it does | Reward | Outcome-only | Flag recall |
|---|---|---|---|---|
| `reference` | All six tools, the oracle's decision, only derived exemptions | **1.00** | 1.00 | 100% |
| `always_flag` | Full evidence, always flags | 0.25 | 0.25 | **100%** |
| `always_escalate` | Full evidence, always escalates | -0.04 | -0.04 | 100% |
| `always_clear` | Full evidence, always clears | -0.10 | -0.10 | 0% |
| `blind_always_clear` | No evidence, always clears | -0.50 | -0.10 | 0% |
| `no_evidence_guesser` | Handed the right label, calls no tools | 0.00 | 1.00 | 100% |
| `citation_fabricator` | Right label, also cites an id that never existed | 0.00 | 1.00 | 100% |
| `exemption_claimer` | Right label, always claims 10b5-1 | 0.10 | 1.00 | 100% |
| `tool_spammer` | Calls tools until the budget ends | -0.50 | n/a | n/a |

<figure markdown>
![Outcome-only versus trajectory-aware score per policy](../assets/rl-policy-scores-light.svg#only-light)
![Outcome-only versus trajectory-aware score per policy](../assets/rl-policy-scores-dark.svg#only-dark)
<figcaption markdown>Mean over the ten canonical scenarios, n=10. Generated from `frontend/src/generated/rl-policies.json`</figcaption>
</figure>

!!! warning "What the reference score does and does not show"
    The reference reaching 1.00 on all ten scenarios is a **consistency check**
    of the environment and reward. The reference reuses the oracle's decision
    logic and the scenario labels were designed to match it, so it is not a
    performance claim. The informative column is the other one: every shortcut
    loses, and each loses for a specific reason.

Every number here: n=10, labels designed by construction
(`data/scenarios.py`), scorer is the scripted stand-in (`evals/oracle.py`), model
version n/a, no uncertainty computed. n=10 supports no precision claim. The
table is deterministic and is regenerated from the code at every commit.

!!! note "Scenario ids in the data"
    Accession numbers and some party names carry a `SCENARIO-` prefix
    (`data/scenarios.py`). The environment does not return the label, scenario id
    or name, but a policy trained on it could key on that prefix. This is a
    verifier demonstration, not a training set.

## What each shortcut shows

| Policy | Outcome-only scoring says | The reward says | Product behaviour it protects |
|---|---|---|---|
| `always_flag` | 100% flag recall | 0.25, far below the reference | Alert fatigue: analysts drown in false positives |
| `no_evidence_guesser` | Right on every case | 0.00 | A finding must rest on gathered evidence, not a lucky guess |
| `citation_fabricator` | Right on every case | 0.00 | Every assertion traces to a retrieved fact |
| `exemption_claimer` | Mostly right | 0.10 | A 10b5-1 narrative must be backed by the filing's own flag |
| `blind_always_clear` | n/a | -0.50, below the same answers with evidence | Skipping evidence must never beat gathering it |
| `tool_spammer` | n/a | -0.50 | The per-investigation cost guardrail |

## Gate

`make eval` runs the canonical eval and then `evals/run_rl.py`, in CI on every
pull request. It fails if any of these is false:

- the reference mean is exactly 1.00 and every reference episode ends in a submit;
- every other policy scores at least 0.5 below the reference;
- skipping evidence never scores above gathering it for the same answers;
- no observation contains a scenario id or name.

A further CI step fails if the generated results file differs from the
committed one. The scorer is the scripted stand-in; **no live-model number is
gated.**

## Live-model runs (not gated)

The same ten scenarios were run through the real graph with real models and
scored with the same `compute_reward` (`make eval-live`, `evals/live_run.py`).
This is **not** part of `make eval` and no CI check depends on it. Models:
`gpt-4o-mini-2024-07-18` (plan, investigate, claims) and `gpt-4o-2024-08-06`
(finding, judge). Labels were designed with the scenarios, as above.

| Run | Claim extractor | Correct | Audit = 0 | Unsupported claims per run | Mean reward (outcome only) | Cost |
|---|---|---|---|---|---|---|
| 2026-10-29 | v1 | 4/10 | 5/10 | 3.2 | -0.03 (0.09) | $0.43 |
| 2026-10-31 | v1 | 5/10 | 8/10 | 3.2 | -0.24 (0.28) | $0.41 |
| 2026-11-01 | **v2** | 5/10 | **0/10** | **1.5** | **+0.15** (0.22) | $0.40 |

n=10 per run, one run each. No uncertainty is computed; n=10 supports no
precision claim, and one run varies from the next. Per-scenario results and every
transcript are in `evals/recordings/live-*/`, and the `/evaluation` page renders
the same numbers from `frontend/src/generated/live-runs.json`.

What the runs show:

- **The audit found a real defect, and it was fixed.** In the v1 runs the claim
  extractor cited no tool-call ids on 5 and then 8 of 10 runs, so the audit's
  citation check scored those runs 0 and the grounding judge rejected the claims
  as uncited. Structured output was already strict, so the field wasn't missing:
  the model chose an empty list because it saw only opaque ids like
  `call_E40B…`. Extractor v2 (`prompts/claim_extractor_v2.md`) gets one line per
  call: id, tool name, arguments and a truncated result. With that, no run scored
  0 and unsupported claims halved. Invented ids are still left in place for the
  audit to report, not filtered out.
- **The fix did not change the answers.** Accuracy stayed at 5 of 10, and the
  model still clears three of the four `flag` cases, which the outcome table
  penalises hardest. That is a disposition-reasoning problem, not a citation one,
  and it is still open.
- **A record-only audit and the grounding judge do different jobs.** The judge
  sees only the claims it is given; the audit surfaced the extractor weakness that
  the grounding report alone did not explain.

The recorded transcripts are what a later replay harness would use to replace the
scripted stand-in (`evals/oracle.py`) with real responses. That replacement is not
built yet.

## Lessons learned

1. **Outcome-only scoring rewards `always_flag`.** It gets 100% flag recall while
   being wrong on six of ten cases.
2. **Scaling penalties by the trajectory score makes skipping evidence the best
   strategy when unsure.** A wrong answer multiplied by zero is zero, which beats
   a thorough wrong answer. Penalties are therefore never scaled
   ([D-A2-8](../architecture/decisions/D-A2-8-reward-design.md)).
3. **Harness-building already exposed two scenarios that were trivially
   passable** ([Evaluation](evaluation.md)). The RL gate applies the same
   discipline to the reward.
4. **The first version of the gate could not catch two deliberate bugs.**
   Breaking the reward so penalties were scaled, or removing the fabricated-id
   check, both left the gate green: no policy gave a wrong answer without
   evidence, and the fabricator cited only ghost ids, which a weaker check also
   zeroes. Adding `blind_always_clear` and making the fabricator cite one real
   and one invented id fixed both, and each mutation now fails `make eval`. A
   gate that has never been seen to fail is not evidence.
