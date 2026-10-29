import json
from collections.abc import Iterator

import pytest
from gymnasium.utils.env_checker import check_env

from data.scenarios import SCENARIOS
from evals.rl_env import (
    EFFICIENCY_PENALTY,
    INVALID_ACTION_PENALTY,
    OUTCOME_TABLE,
    SurveillanceEnv,
    compute_reward,
)
from evals.rl_policies import ANSWER_KEY, ReferencePolicy
from evals.run_rl import _outcomes, run_rl_eval
from surveillance.schemas.finding import ProcessAudit

SCENARIO_01 = SCENARIOS[0]
SCENARIO_05 = SCENARIOS[4]
SCENARIO_07 = SCENARIOS[6]


@pytest.fixture(scope="module")
def env() -> Iterator[SurveillanceEnv]:
    environment = SurveillanceEnv()
    yield environment
    environment.close()


def _audit(trajectory: float) -> ProcessAudit:
    return ProcessAudit(
        mandatory_tools_called=[],
        mandatory_tools_missing=[],
        coverage=1.0,
        details_first=True,
        fabricated_citation_ids=[],
        citation_validity=1.0,
        claimed_exemptions=[],
        unsupported_exemptions=[],
        exemption_validity=1.0,
        trajectory_score=trajectory,
    )


def _submit(
    disposition: str, cited: list[str], exemptions: list[dict[str, object]] | None = None
) -> str:
    return json.dumps(
        {
            "type": "submit",
            "disposition": disposition,
            "claims": [{"text": "claim", "cited_tool_call_ids": cited}],
            "exemptions": exemptions or [],
        }
    )


def _call(name: str, args: dict[str, object] | None = None) -> str:
    return json.dumps({"type": "tool_call", "name": name, "args": args or {}})


def _play_reference(env: SurveillanceEnv, scenario_id: str) -> tuple[list[str], dict[str, object]]:
    observation, info = env.reset(options={"scenario_id": scenario_id})
    seen = [observation, json.dumps(info)]
    policy = ReferencePolicy()
    policy.begin(observation)
    while True:
        observation, _, terminated, truncated, info = env.step(policy.act(observation))
        seen.append(observation)
        if terminated or truncated:
            return seen, info


def test_check_env_passes() -> None:
    environment = SurveillanceEnv()
    try:
        check_env(environment, skip_render_check=True)
    finally:
        environment.close()


def test_reset_is_deterministic_for_the_same_seed_and_scenario(env: SurveillanceEnv) -> None:
    options = {"scenario_id": SCENARIO_01.id}
    first, _ = env.reset(seed=7, options=options)
    second, _ = env.reset(seed=7, options=options)
    assert first == second


def test_seed_without_scenario_picks_the_same_scenario(env: SurveillanceEnv) -> None:
    first, _ = env.reset(seed=3)
    second, _ = env.reset(seed=3)
    assert first == second


def test_unknown_scenario_is_rejected(env: SurveillanceEnv) -> None:
    with pytest.raises(ValueError, match="unknown scenario_id"):
        env.reset(options={"scenario_id": "nope"})


def test_no_observation_or_info_reveals_a_scenario_id_or_name(env: SurveillanceEnv) -> None:
    for scenario in SCENARIOS:
        seen, _ = _play_reference(env, scenario.id)
        text = "\n".join(seen).lower()
        assert scenario.id.lower() not in text
        assert scenario.name.lower() not in text
        assert "expected" not in text


def test_reference_policy_gets_full_marks_on_every_scenario(env: SurveillanceEnv) -> None:
    for scenario in SCENARIOS:
        _, info = _play_reference(env, scenario.id)
        assert info["reward_breakdown"]["total"] == 1.0, scenario.id  # type: ignore[index]


def test_tool_call_ids_are_sequential(env: SurveillanceEnv) -> None:
    env.reset(options={"scenario_id": SCENARIO_01.id})
    first, *_ = env.step(_call("get_compliance_rules"))
    second, *_ = env.step(_call("get_compliance_rules"))
    assert [json.loads(first)["tool_call_id"], json.loads(second)["tool_call_id"]] == ["t1", "t2"]


@pytest.mark.parametrize(("expected", "submitted"), list(OUTCOME_TABLE))
def test_outcome_table_entries_apply_with_a_perfect_trajectory(
    expected: str, submitted: str
) -> None:
    breakdown = compute_reward(expected, submitted, _audit(1.0), tool_calls=6, invalid_actions=0)  # type: ignore[arg-type]
    assert breakdown.total == OUTCOME_TABLE[(expected, submitted)]  # type: ignore[index]


def test_positive_outcome_is_scaled_by_the_trajectory_score() -> None:
    breakdown = compute_reward("flag", "flag", _audit(0.5), tool_calls=6, invalid_actions=0)
    assert breakdown.total == 0.5


def test_penalties_are_never_scaled_by_the_trajectory_score() -> None:
    # Scaling a wrong answer by 0 would make skipping all evidence the best strategy.
    skipped = compute_reward("flag", "clear", _audit(0.0), tool_calls=0, invalid_actions=0)
    thorough = compute_reward("flag", "clear", _audit(1.0), tool_calls=6, invalid_actions=0)
    assert skipped.total == thorough.total == OUTCOME_TABLE[("flag", "clear")]


def test_calls_beyond_the_six_mandatory_ones_cost_a_little() -> None:
    breakdown = compute_reward("clear", "clear", _audit(1.0), tool_calls=9, invalid_actions=0)
    assert breakdown.total == pytest.approx(1.0 - 3 * EFFICIENCY_PENALTY)


def test_invalid_actions_are_added_at_the_end(env: SurveillanceEnv) -> None:
    env.reset(options={"scenario_id": SCENARIO_01.id})
    _, reward, terminated, truncated, info = env.step("not json")
    assert (reward, terminated, truncated) == (0.0, False, False)
    assert "invalid_action" in info
    _, reward, terminated, _, info = env.step(_submit("flag", []))
    assert terminated
    assert info["reward_breakdown"]["invalid_penalty"] == INVALID_ACTION_PENALTY
    assert reward == info["reward_breakdown"]["total"]


@pytest.mark.parametrize(
    "action",
    [
        _call("no_such_tool"),
        _call("get_transaction_details", {"wrong": 1}),
        json.dumps({"type": "submit", "disposition": "maybe"}),
        json.dumps({"type": "dance"}),
        "[]",
    ],
)
def test_bad_actions_are_invalid_and_the_episode_continues(
    env: SurveillanceEnv, action: str
) -> None:
    env.reset(options={"scenario_id": SCENARIO_01.id})
    _, reward, terminated, truncated, info = env.step(action)
    assert (reward, terminated, truncated) == (0.0, False, False)
    assert "invalid_action" in info


def test_exceeding_the_budget_truncates_with_a_fixed_penalty() -> None:
    environment = SurveillanceEnv(max_tool_calls=3)
    try:
        environment.reset(options={"scenario_id": SCENARIO_01.id})
        for _ in range(3):
            environment.step(_call("get_compliance_rules"))
        _, reward, terminated, truncated, _ = environment.step(_call("get_compliance_rules"))
    finally:
        environment.close()
    assert (reward, terminated, truncated) == (-0.5, False, True)


def test_submitting_is_always_allowed_at_the_budget_limit() -> None:
    environment = SurveillanceEnv(max_tool_calls=1)
    try:
        environment.reset(options={"scenario_id": SCENARIO_01.id})
        environment.step(_call("get_compliance_rules"))
        _, _, terminated, truncated, _ = environment.step(_submit("flag", ["t1"]))
    finally:
        environment.close()
    assert terminated
    assert not truncated


def test_step_after_the_episode_ends_is_an_error(env: SurveillanceEnv) -> None:
    env.reset(options={"scenario_id": SCENARIO_01.id})
    env.step(_submit("flag", []))
    with pytest.raises(RuntimeError, match="episode is over"):
        env.step(_submit("flag", []))


def test_fabricated_citations_zero_a_correct_answer(env: SurveillanceEnv) -> None:
    observation, _ = env.reset(options={"scenario_id": SCENARIO_01.id})
    policy = ReferencePolicy()
    policy.begin(observation)
    for _ in range(6):
        observation, *_ = env.step(policy.act(observation))
    _, reward, terminated, _, info = env.step(
        _submit(ANSWER_KEY[SCENARIO_01.accession_number], ["ghost"])
    )
    assert terminated
    assert reward == 0.0
    assert info["process_audit"]["fabricated_citation_ids"] == ["ghost"]


def test_unsupported_exemption_zeroes_a_correct_answer(env: SurveillanceEnv) -> None:
    observation, _ = env.reset(options={"scenario_id": SCENARIO_01.id})
    policy = ReferencePolicy()
    policy.begin(observation)
    for _ in range(6):
        observation, *_ = env.step(policy.act(observation))
    _, reward, _, _, _ = env.step(_submit("flag", ["t1"], [{"kind": "reported_under_10b5_1"}]))
    assert reward == 0.0


def test_a_real_10b5_1_exemption_is_not_penalised(env: SurveillanceEnv) -> None:
    observation, _ = env.reset(options={"scenario_id": SCENARIO_05.id})
    policy = ReferencePolicy()
    policy.begin(observation)
    for _ in range(6):
        observation, *_ = env.step(policy.act(observation))
    _, reward, _, _, _ = env.step(_submit("clear", ["t1"], [{"kind": "reported_under_10b5_1"}]))
    assert reward == 1.0


def test_f_line_exemption_does_not_extend_to_the_unrelated_s_line(env: SurveillanceEnv) -> None:
    env.reset(options={"scenario_id": SCENARIO_07.id})
    observation, *_ = env.step(
        _call("get_transaction_details", {"accession_number": SCENARIO_07.accession_number})
    )
    lines = json.loads(observation)["result"]["transactions"]
    f_sk = next(line["nonderiv_trans_sk"] for line in lines if line["trans_code"] == "F")
    s_sk = next(line["nonderiv_trans_sk"] for line in lines if line["trans_code"] == "S")

    def audit_for(sk: int) -> dict[str, object]:
        environment = SurveillanceEnv()
        try:
            environment.reset(options={"scenario_id": SCENARIO_07.id})
            environment.step(
                _call("get_transaction_details", {"accession_number": SCENARIO_07.accession_number})
            )
            *_, info = environment.step(
                _submit("escalate", ["t1"], [{"kind": "tax_withholding", "transaction_sk": sk}])
            )
        finally:
            environment.close()
        return info["process_audit"]  # type: ignore[no-any-return]

    assert audit_for(f_sk)["unsupported_exemptions"] == []
    assert audit_for(s_sk)["unsupported_exemptions"]


def test_the_gate_passes_for_the_shipped_policies() -> None:
    results = run_rl_eval()
    failed = [o.case_id for o in _outcomes(results) if not o.passed]
    assert failed == []
