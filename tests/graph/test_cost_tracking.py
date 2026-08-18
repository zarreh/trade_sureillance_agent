from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult

from surveillance.graph.cost_tracking import CostTrackingHandler
from surveillance.graph.policies import FAST_MODEL, REASONING_MODEL


def _llm_result(model: str, prompt_tokens: int, completion_tokens: int) -> LLMResult:
    return LLMResult(
        generations=[[ChatGeneration(message=AIMessage(content="ok"))]],
        llm_output={
            "model_name": model,
            "token_usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens},
        },
    )


def test_on_llm_end_attributes_cost_to_the_langgraph_node() -> None:
    handler = CostTrackingHandler()
    handler.on_llm_end(
        _llm_result(FAST_MODEL, 1000, 200),
        run_id="00000000-0000-0000-0000-000000000001",  # type: ignore[arg-type]
        metadata={"langgraph_node": "plan"},
    )

    assert len(handler.entries) == 1
    entry = handler.entries[0]
    assert entry.node == "plan"
    assert entry.model == FAST_MODEL
    assert entry.prompt_tokens == 1000
    assert entry.completion_tokens == 200
    assert entry.cost_usd > 0


def test_reasoning_model_costs_more_per_token_than_fast_model() -> None:
    handler = CostTrackingHandler()
    handler.on_llm_end(
        _llm_result(FAST_MODEL, 1000, 1000),
        run_id="00000000-0000-0000-0000-000000000001",  # type: ignore[arg-type]
        metadata={"langgraph_node": "plan"},
    )
    handler.on_llm_end(
        _llm_result(REASONING_MODEL, 1000, 1000),
        run_id="00000000-0000-0000-0000-000000000002",  # type: ignore[arg-type]
        metadata={"langgraph_node": "draft_finding"},
    )

    fast_cost, reasoning_cost = (e.cost_usd for e in handler.entries)
    assert reasoning_cost > fast_cost


def test_missing_metadata_falls_back_to_unknown_node() -> None:
    handler = CostTrackingHandler()
    handler.on_llm_end(
        _llm_result(FAST_MODEL, 10, 5),
        run_id="00000000-0000-0000-0000-000000000001",  # type: ignore[arg-type]
    )

    assert handler.entries[0].node == "unknown"


def test_missing_token_usage_yields_zero_cost() -> None:
    handler = CostTrackingHandler()
    result = LLMResult(
        generations=[[ChatGeneration(message=AIMessage(content="ok"))]],
        llm_output={"model_name": FAST_MODEL},
    )
    handler.on_llm_end(result, run_id="00000000-0000-0000-0000-000000000001")  # type: ignore[arg-type]

    entry = handler.entries[0]
    assert entry.prompt_tokens == 0
    assert entry.completion_tokens == 0
    assert entry.cost_usd == 0.0
