"""Per-investigation cost guardrail (docs/PLAN.md §5.5).

The ceiling and the LangChain-messages counting are provided by
`zarreh_agentkit.guardrails.budget` (extracted here and in A3, converging on
an identical shape). This module adapts the kit's message-count-agnostic
signature back to the messages-based one this app's call sites already use,
and keeps the app's own choice of what a breach means: on breach the run
terminates with a partial finding marked `incomplete` — it never silently
truncates. That is what makes the per-investigation cost figure honest and
keeps a public demo from running unbounded.
"""

from __future__ import annotations

from collections.abc import Sequence

from langchain_core.messages import BaseMessage
from zarreh_agentkit.guardrails.budget import Budget, count_tool_calls
from zarreh_agentkit.guardrails.budget import budget_breach_reason as _budget_breach_reason

DEFAULT_BUDGET = Budget()

__all__ = ["Budget", "DEFAULT_BUDGET", "budget_breach_reason", "count_tool_calls"]


def budget_breach_reason(
    messages: Sequence[BaseMessage], started_at: float, budget: Budget = DEFAULT_BUDGET
) -> str | None:
    """Returns a human-readable breach reason, or None if within budget."""
    return _budget_breach_reason(count_tool_calls(messages), started_at, budget)
