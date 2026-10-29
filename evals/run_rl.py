"""CLI and CI gate for the RL environment (wired into `make eval`).

Runs every scripted policy on the ten canonical scenarios and gates on three
things: the reference policy scores exactly 1.00 and always submits (a
consistency check of the environment and reward, not a performance claim),
every other policy scores at least 0.5 below it, and no observation leaks a
scenario id or name. The scorer is the scripted stand-in in `evals/oracle.py`;
no live model is involved.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from zarreh_agentkit.evals import EvalOutcome, run_eval_cli

from data.scenarios import SCENARIOS, Scenario
from evals.metrics import EvalResult, compute_metrics
from evals.rl_env import RewardBreakdown, SurveillanceEnv
from evals.rl_policies import Policy, build_policies

RESULTS_PATH = Path(__file__).parent.parent / "frontend" / "src" / "generated" / "rl-policies.json"
MARGIN = 0.5


@dataclass(frozen=True)
class Episode:
    policy: str
    scenario_id: str
    expected: str
    submitted: str | None
    terminated: bool
    breakdown: RewardBreakdown


@dataclass(frozen=True)
class RLResults:
    episodes: list[Episode]
    descriptions: dict[str, str]
    leaked: bool

    def policy_names(self) -> list[str]:
        return list(self.descriptions)

    def for_policy(self, name: str) -> list[Episode]:
        return [e for e in self.episodes if e.policy == name]

    def mean(self, name: str) -> float:
        rows = self.for_policy(name)
        return sum(e.breakdown.total for e in rows) / len(rows)

    def outcome_only_mean(self, name: str) -> float | None:
        rows = self.for_policy(name)
        if any(e.submitted is None for e in rows):
            return None
        return sum(e.breakdown.outcome for e in rows) / len(rows)


def _leaks(texts: list[str], scenario: Scenario) -> bool:
    haystack = "\n".join(texts).lower()
    return scenario.id.lower() in haystack or scenario.name.lower() in haystack


def _run_episode(env: SurveillanceEnv, policy: Policy, scenario: Scenario) -> tuple[Episode, bool]:
    observation, info = env.reset(options={"scenario_id": scenario.id})
    seen = [observation, json.dumps(info)]
    policy.begin(observation)
    while True:
        observation, _, terminated, truncated, info = env.step(policy.act(observation))
        seen += [observation]
        if terminated or truncated:
            break
    breakdown = RewardBreakdown(**info["reward_breakdown"])
    episode = Episode(
        policy=policy.name,
        scenario_id=scenario.id,
        expected=scenario.expected_disposition,
        submitted=info.get("submitted"),
        terminated=terminated,
        breakdown=breakdown,
    )
    # The terminal info is the reward, which legitimately reveals the outcome, so it is not scanned.
    return episode, _leaks(seen, scenario)


def run_rl_eval() -> RLResults:
    env = SurveillanceEnv()
    episodes: list[Episode] = []
    leaked = False
    policies = build_policies()
    try:
        for policy in policies:
            for scenario in SCENARIOS:
                episode, leak = _run_episode(env, policy, scenario)
                episodes.append(episode)
                leaked = leaked or leak
    finally:
        env.close()
    return RLResults(episodes, {p.name: p.description for p in policies}, leaked)


def _outcomes(results: RLResults) -> list[EvalOutcome]:
    reference = results.mean("reference")
    outcomes = [
        EvalOutcome("reference:mean==1.00", abs(reference - 1.0) < 1e-9),
        EvalOutcome(
            "reference:every-episode-submitted",
            all(e.terminated for e in results.for_policy("reference")),
        ),
        EvalOutcome("no-observation-leakage", not results.leaked),
        # Wrong answers must cost the same whether or not evidence was gathered.
        EvalOutcome(
            "skipping-evidence-never-beats-gathering-it",
            results.mean("blind_always_clear") < results.mean("always_clear"),
        ),
    ]
    for name in results.policy_names():
        if name != "reference":
            outcomes.append(
                EvalOutcome(
                    f"{name}:mean<=reference-{MARGIN}", results.mean(name) <= reference - MARGIN
                )
            )
    return outcomes


def _metrics_for(results: RLResults, name: str) -> tuple[float, float] | None:
    rows = results.for_policy(name)
    if any(e.submitted is None for e in rows):
        return None
    # Only the label-based metrics are meaningful here; the other fields are neutral.
    metrics = compute_metrics(
        [
            EvalResult(
                scenario_id=e.scenario_id,
                expected_disposition=e.expected,  # type: ignore[arg-type]
                actual_disposition=e.submitted,  # type: ignore[arg-type]
                plan_ok=True,
                total_claims=0,
                claims_with_citation=0,
                unsupported_claims=0,
                cost_usd=0.0,
                latency_seconds=0.0,
            )
            for e in rows
        ]
    )
    return metrics.flag_recall, metrics.false_positive_rate_on_clear


def _print_report(results: RLResults) -> None:
    n = len(SCENARIOS)
    print(f"RL gate: n={n} scenarios x {len(results.policy_names())} scripted policies")
    print("scorer: scripted stand-in (evals/oracle.py); no live model\n")
    print(f"{'policy':22} {'reward':>8} {'outcome-only':>13} {'flag recall':>12}")
    for name in results.policy_names():
        outcome_only = results.outcome_only_mean(name)
        metrics = _metrics_for(results, name)
        print(
            f"{name:22} {results.mean(name):8.3f} "
            f"{'n/a' if outcome_only is None else f'{outcome_only:13.3f}':>13} "
            f"{'n/a' if metrics is None else f'{metrics[0]:12.0%}':>12}"
        )
    print()
    for outcome in _outcomes(results):
        print(f"{'ok  ' if outcome.passed else 'FAIL'} {outcome.case_id}")


def _round(value: float) -> float:
    return round(value, 6) + 0.0


def results_to_json(results: RLResults) -> str:
    policies = []
    for name in results.policy_names():
        metrics = _metrics_for(results, name)
        outcome_only = results.outcome_only_mean(name)
        policies.append(
            {
                "policy": name,
                "description": results.descriptions[name],
                "reward_mean": _round(results.mean(name)),
                "outcome_only_mean": None if outcome_only is None else _round(outcome_only),
                "flag_recall": None if metrics is None else _round(metrics[0]),
                "false_positive_rate_on_clear": None if metrics is None else _round(metrics[1]),
                "per_scenario": [
                    {
                        "scenario_id": e.scenario_id,
                        "reward": _round(e.breakdown.total),
                        "outcome_only": None
                        if e.submitted is None
                        else _round(e.breakdown.outcome),
                    }
                    for e in results.for_policy(name)
                ],
            }
        )
    document = {
        "n": len(SCENARIOS),
        "scorer": "scripted stand-in (evals/oracle.py); no live model",
        "label_source": "canonical scenarios in data/scenarios.py, designed with their labels",
        "model_version": "n/a, stand-in",
        "run_date": "n/a (deterministic; regenerated from the code at each commit)",
        "uncertainty": "none computed; n=10 supports no precision claim",
        "gate_margin": MARGIN,
        "policies": policies,
    }
    return json.dumps(document, indent=2) + "\n"


def main() -> int:
    results = run_rl_eval()
    code = run_eval_cli(lambda: results, _print_report, _outcomes)
    if code == 0:
        RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESULTS_PATH.write_text(results_to_json(results))
    return code


if __name__ == "__main__":
    sys.exit(main())
