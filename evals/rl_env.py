"""The investigation loop as a Gymnasium environment, with a reward built from
the product's own process audit (docs/architecture/decisions/D-A2-8).

Why it exists: it shows how the product's checks work as a verifier and a
reward, and lets a CI gate prove that shortcut and gaming policies cannot
score well. It is an extra on top of the surveillance product, not the point.

Observations and actions are JSON strings, which is what an LLM policy would
emit. Only the six real tools run; the plan, judge and finding nodes do not.
The wall-clock budget is deliberately not enforced: it would make episodes
nondeterministic.
"""

from __future__ import annotations

import json
import shutil
import string
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

import gymnasium as gym
from gymnasium import spaces
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, ValidationError

from data.scenarios import SCENARIOS, Scenario
from evals.canonical import _build_eval_stores
from surveillance.graph.budget import DEFAULT_BUDGET
from surveillance.graph.nodes.check_plan import MANDATORY_TOOLS
from surveillance.graph.trajectory_audit import audit_trajectory, extract_claimed_exemptions
from surveillance.schemas.finding import ClaimedExemption, ProcessAudit, ToolCallRecord
from surveillance.schemas.grounding import Claim
from surveillance.tools.registry import build_tools

Disposition = Literal["clear", "flag", "escalate"]

# Gymnasium's default Text charset is alphanumeric only, so JSON would never fit.
CHARSET = string.printable
OBSERVATION_MAX_LENGTH = 20_000
ACTION_MAX_LENGTH = 8_192

INVALID_ACTION_PENALTY = 0.05
EFFICIENCY_PENALTY = 0.01
TRUNCATION_PENALTY = 0.5

# Missing a violation is worse than over-alerting; a severity miss (flag vs
# escalate) is milder than a wrong direction; alert fatigue is the cost of a
# false positive (docs/evidence/false-positives.md).
OUTCOME_TABLE: dict[tuple[Disposition, Disposition], float] = {
    ("clear", "clear"): 1.0,
    ("flag", "flag"): 1.0,
    ("escalate", "escalate"): 1.0,
    ("clear", "flag"): -0.25,
    ("clear", "escalate"): -0.5,
    ("flag", "clear"): -0.75,
    ("flag", "escalate"): -0.10,
    ("escalate", "flag"): -0.25,
    ("escalate", "clear"): -1.0,
}


@dataclass(frozen=True)
class RewardBreakdown:
    outcome: float
    trajectory: float
    scaled_outcome: float
    efficiency_penalty: float
    invalid_penalty: float
    total: float
    truncated: bool = False


def compute_reward(
    expected: Disposition,
    submitted: Disposition,
    audit: ProcessAudit,
    tool_calls: int,
    invalid_actions: int,
) -> RewardBreakdown:
    outcome = OUTCOME_TABLE[(expected, submitted)]
    trajectory = audit.trajectory_score
    # Only a positive outcome is scaled. Scaling a penalty by the trajectory score would turn
    # every wrong answer into 0 for an agent that skips all evidence, so skipping would win.
    scaled = outcome * trajectory if outcome > 0 else outcome
    efficiency = EFFICIENCY_PENALTY * max(0, tool_calls - len(MANDATORY_TOOLS))
    invalid = INVALID_ACTION_PENALTY * invalid_actions
    return RewardBreakdown(
        outcome=outcome,
        trajectory=trajectory,
        scaled_outcome=scaled,
        efficiency_penalty=efficiency,
        invalid_penalty=invalid,
        total=scaled - efficiency - invalid,
    )


def truncation_reward() -> RewardBreakdown:
    return RewardBreakdown(0.0, 0.0, 0.0, 0.0, 0.0, -TRUNCATION_PENALTY, truncated=True)


class _SubmittedClaim(BaseModel):
    text: str
    cited_tool_call_ids: list[str] = Field(default_factory=list)


class _Submission(BaseModel):
    type: Literal["submit"]
    disposition: Disposition
    claims: list[_SubmittedClaim] = Field(default_factory=list)
    exemptions: list[ClaimedExemption] = Field(default_factory=list)


class _ToolCall(BaseModel):
    type: Literal["tool_call"]
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


def _printable(text: str) -> str:
    return "".join(c if c in CHARSET else "?" for c in text)


def _encode(payload: object) -> str:
    return _printable(json.dumps(payload))


class SurveillanceEnv(gym.Env[str, str]):
    metadata: dict[str, Any] = {"render_modes": []}  # noqa: RUF012

    def __init__(self, max_tool_calls: int = DEFAULT_BUDGET.max_tool_calls) -> None:
        self.observation_space = spaces.Text(
            min_length=0, max_length=OBSERVATION_MAX_LENGTH, charset=CHARSET
        )
        self.action_space = spaces.Text(min_length=0, max_length=ACTION_MAX_LENGTH, charset=CHARSET)
        self._max_tool_calls = max_tool_calls
        self._tmp: tempfile.TemporaryDirectory[str] | None = None
        self._tools: dict[str, StructuredTool] = {}
        self._episodes = 0
        self._scenario: Scenario | None = None
        self._records: list[ToolCallRecord] = []
        self._budget_used = 0
        self._invalid_actions = 0
        self._done = True

    def _ensure_stores(self) -> None:
        if self._tools:
            return
        self._tmp = tempfile.TemporaryDirectory()
        fact_store, policy_store = _build_eval_stores(Path(self._tmp.name))
        self._tools = {t.name: t for t in build_tools(fact_store, policy_store)}

    def close(self) -> None:
        if self._tmp is not None:
            shutil.rmtree(self._tmp.name, ignore_errors=True)
            self._tmp = None
        self._tools = {}

    def reset(
        self, *, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[str, dict[str, Any]]:
        super().reset(seed=seed)
        self._ensure_stores()
        scenario_id = (options or {}).get("scenario_id")
        if scenario_id is None:
            scenario = SCENARIOS[int(self.np_random.integers(len(SCENARIOS)))]
        else:
            matches = [s for s in SCENARIOS if s.id == scenario_id]
            if not matches:
                raise ValueError(f"unknown scenario_id {scenario_id!r}")
            scenario = matches[0]
        self._scenario = scenario
        self._records = []
        self._budget_used = 0
        self._invalid_actions = 0
        self._done = False
        self._episodes += 1

        observation = {
            "accession_number": scenario.accession_number,
            "tools": [
                {
                    "name": name,
                    "args_schema": tool.get_input_jsonschema(),
                }
                for name, tool in self._tools.items()
            ],
            "budget": {"max_tool_calls": self._max_tool_calls},
        }
        return _encode(observation), {"episode_id": f"ep-{self._episodes}"}

    def step(self, action: str) -> tuple[str, float, bool, bool, dict[str, Any]]:
        if self._done or self._scenario is None:
            raise RuntimeError("the episode is over; call reset()")
        try:
            payload: object = json.loads(action)
        except json.JSONDecodeError:
            payload = None

        try:
            submission = _Submission.model_validate(payload)
        except ValidationError:
            submission = None
        if submission is not None:
            return self._finish(submission)

        if self._budget_used >= self._max_tool_calls:
            self._done = True
            breakdown = truncation_reward()
            info = {"reward_breakdown": asdict(breakdown), "tool_calls": len(self._records)}
            return _encode({"status": "truncated"}), breakdown.total, False, True, info
        self._budget_used += 1

        try:
            call = _ToolCall.model_validate(payload)
        except ValidationError:
            return self._invalid("action is neither a valid tool_call nor a valid submit")
        tool = self._tools.get(call.name)
        if tool is None:
            return self._invalid(f"unknown tool {call.name!r}")
        try:
            # Any failure here is the policy's bad arguments, scored as an invalid action.
            result = str(tool.invoke(call.args))
        except Exception as exc:
            return self._invalid(f"bad arguments for {call.name}: {type(exc).__name__}")

        call_id = f"t{len(self._records) + 1}"
        self._records.append(
            ToolCallRecord(tool_call_id=call_id, tool_name=call.name, args=call.args, result=result)
        )
        try:
            parsed: object = json.loads(result)
        except json.JSONDecodeError:
            parsed = result
        return _encode({"tool_call_id": call_id, "result": parsed}), 0.0, False, False, {}

    def _invalid(self, reason: str) -> tuple[str, float, bool, bool, dict[str, Any]]:
        self._invalid_actions += 1
        return _encode({"error": reason}), 0.0, False, False, {"invalid_action": reason}

    def _finish(self, submission: _Submission) -> tuple[str, float, bool, bool, dict[str, Any]]:
        assert self._scenario is not None
        claims = [
            Claim(id=f"c{i}", text=c.text, cited_tool_call_ids=c.cited_tool_call_ids)
            for i, c in enumerate(submission.claims, start=1)
        ]
        claimed = list(submission.exemptions)
        explicit_kinds = {e.kind for e in claimed}
        claimed += [e for e in extract_claimed_exemptions(claims) if e.kind not in explicit_kinds]
        audit = audit_trajectory(self._records, claims, claimed)
        breakdown = compute_reward(
            self._scenario.expected_disposition,
            submission.disposition,
            audit,
            tool_calls=len(self._records),
            invalid_actions=self._invalid_actions,
        )
        self._done = True
        info = {
            "reward_breakdown": asdict(breakdown),
            "process_audit": audit.model_dump(),
            "submitted": submission.disposition,
            "tool_calls": len(self._records),
        }
        return _encode({"status": "submitted"}), breakdown.total, True, False, info
