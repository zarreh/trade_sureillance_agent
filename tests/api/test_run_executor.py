from typing import TypedDict

from langgraph.graph import END, StateGraph

from surveillance.api.run_executor import WithRecursionLimit


class _State(TypedDict):
    n: int


def _counting_graph(steps: int) -> object:
    workflow = StateGraph(_State)
    workflow.add_node("step", lambda s: {"n": s["n"] + 1})
    workflow.set_entry_point("step")
    workflow.add_conditional_edges("step", lambda s: "step" if s["n"] < steps else END)
    return workflow.compile()


async def _run(graph: object) -> int:
    count = 0
    async for event in graph.astream_events({"n": 0}, config={"callbacks": []}, version="v2"):  # type: ignore[attr-defined]
        count += event["event"] == "on_chain_end"
    return count


async def test_a_run_longer_than_the_default_limit_completes() -> None:
    assert await _run(WithRecursionLimit(_counting_graph(40))) > 0


async def test_the_default_limit_would_abort_the_same_run() -> None:
    import pytest
    from langgraph.errors import GraphRecursionError

    with pytest.raises(GraphRecursionError):
        await _run(_counting_graph(40))
