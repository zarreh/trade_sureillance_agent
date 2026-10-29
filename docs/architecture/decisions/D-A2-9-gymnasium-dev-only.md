# D-A2-9: Gymnasium is dev-only and confined to evals

**Status:** Accepted, enforced by an import-linter contract.

## Context

The RL environment subclasses `gymnasium.Env`. The surveillance product must not
depend on it: a reviewer should be able to read, run and deploy the product with
the RL layer removed.

## Decision

`gymnasium` is in the `dev` extra only and is imported only under `evals/`. The
import-linter contract "no DSPy, DeepEval or gymnasium outside evals/optimize"
forbids the `surveillance` package from importing it.

## Consequences

- The production image does not install it.
- The process audit, which the reward reuses, lives in `src/` with no
  `gymnasium` import, so the dependency points one way: `evals` depends on
  `surveillance`, never the reverse.
- Deleting `evals/rl_*.py` leaves the product and its tests intact.
