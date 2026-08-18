"""Investigation-plan schemas — produced by the planner LLM and validated
deterministically by check_plan (docs/PLAN.md §5.3, D-A2-2).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    order: int
    objective: str
    tool: str
    why: str


class InvestigationPlan(BaseModel):
    steps: list[PlanStep]


class PlanCheck(BaseModel):
    """Produced by code, never a model — don't spend a model call on a
    decision an `if` can make (docs/PLAN.md D-A2-2)."""

    ok: bool
    missing_checks: list[str] = Field(default_factory=list)
    unknown_tools: list[str] = Field(default_factory=list)
    ordering_issues: list[str] = Field(default_factory=list)
