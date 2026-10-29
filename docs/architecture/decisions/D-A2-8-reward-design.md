# D-A2-8: Reward design

**Status:** Accepted, implemented in `evals/rl_env.py` (`compute_reward`).

## Context

The RL environment needs a reward. The obvious choice, scoring the submitted
disposition against the label, is the same outcome-only scoring that lets
`always_flag` reach 100% flag recall. And any reward built on a trajectory score
has a trap: scaling a wrong answer by it.

## Decision

An outcome table, a trajectory multiplier applied only to positive outcomes,
unscaled penalties, and no LLM judge.

| Expected, then submitted | Outcome |
|---|---|
| correct | +1.0 |
| clear, then flag | -0.25 |
| clear, then escalate | -0.50 |
| flag, then clear | -0.75 |
| flag, then escalate | -0.10 |
| escalate, then flag | -0.25 |
| escalate, then clear | -1.0 |

- Missing a violation is worse than over-alerting. A severity miss (flag versus
  escalate) is milder than a wrong direction. Alert fatigue is the real cost of a
  false positive ([False positives](../../evidence/false-positives.md)).
- `total = outcome x P` when the outcome is positive, where `P` is the process
  audit's `trajectory_score` ([D-A2-7](D-A2-7-process-audit.md)). Otherwise
  `total = outcome`.
- Then subtract 0.01 per tool call beyond the six mandatory ones and 0.05 per
  invalid action. Truncation by the budget is a flat -0.5.
- **The LLM grounding judge is not part of the reward.** A persuasive claim must
  not raise a score, and the reward must stay deterministic.

## Consequences

- If a wrong answer were multiplied by `P`, an agent that skips all evidence
  (`P = 0`) would turn every wrong answer into 0. Whenever it was unsure,
  skipping evidence would beat investigating. `test_penalties_are_never_scaled_by_the_trajectory_score`
  pins this, and the gate's `blind_always_clear` check catches it end to end.
- The reward is only as strong as the policies that probe it. Two deliberate bugs
  initially passed the gate; see
  [RL environment](../../evidence/rl-environment.md#lessons-learned).
- A reference score of 1.00 is a consistency check, never a performance claim.
