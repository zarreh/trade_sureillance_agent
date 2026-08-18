"""Per-investigation cost guardrail (docs/PLAN.md §5.5).

On breach the run terminates with a partial finding marked `incomplete` — it
never silently truncates. This is what makes the per-investigation cost
figure honest and keeps a public demo from running unbounded.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass

from langchain_core.messages import AIMessage, BaseMessage


@dataclass(frozen=True)
class Budget:
    max_tool_calls: int = 15
    max_wall_clock_seconds: float = 120.0


DEFAULT_BUDGET = Budget()


def count_tool_calls(messages: Sequence[BaseMessage]) -> int:
    return sum(len(m.tool_calls) for m in messages if isinstance(m, AIMessage) and m.tool_calls)


def budget_breach_reason(
    messages: Sequence[BaseMessage], started_at: float, budget: Budget = DEFAULT_BUDGET
) -> str | None:
    """Returns a human-readable breach reason, or None if within budget."""
    calls = count_tool_calls(messages)
    if calls > budget.max_tool_calls:
        return f"exceeded max_tool_calls={budget.max_tool_calls} (used {calls})"
    elapsed = time.time() - started_at
    if elapsed > budget.max_wall_clock_seconds:
        return (
            f"exceeded max_wall_clock_seconds={budget.max_wall_clock_seconds} "
            f"(elapsed {elapsed:.1f}s)"
        )
    return None
