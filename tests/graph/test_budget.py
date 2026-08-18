from langchain_core.messages import AIMessage, HumanMessage

from surveillance.graph.budget import Budget, budget_breach_reason, count_tool_calls


def _ai_with_tool_calls(n: int) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {"name": "get_transaction_details", "args": {}, "id": f"call_{i}"} for i in range(n)
        ],
    )


def test_count_tool_calls_sums_across_messages() -> None:
    messages = [HumanMessage(content="hi"), _ai_with_tool_calls(2), _ai_with_tool_calls(1)]
    assert count_tool_calls(messages) == 3


def test_breach_on_too_many_tool_calls() -> None:
    import time

    messages = [_ai_with_tool_calls(20)]
    reason = budget_breach_reason(messages, time.time(), Budget(max_tool_calls=15))
    assert reason is not None
    assert "max_tool_calls" in reason


def test_breach_on_wall_clock() -> None:
    started_at = 0.0  # epoch start -> guaranteed elapsed
    reason = budget_breach_reason([], started_at, Budget(max_wall_clock_seconds=1.0))
    assert reason is not None
    assert "max_wall_clock_seconds" in reason


def test_no_breach_within_budget() -> None:
    import time

    messages = [_ai_with_tool_calls(2)]
    assert budget_breach_reason(messages, time.time()) is None
