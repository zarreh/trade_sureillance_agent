"""ReAct step: invokes the tool-bound investigator on the running
conversation. Seeds the system+plan messages on the first call only."""

from __future__ import annotations

from collections.abc import Callable

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from surveillance.graph.protocols import Investigator
from surveillance.graph.state import SurveillanceState


def _seed_messages(state: SurveillanceState, system_prompt: str) -> list[BaseMessage]:
    plan = state["plan"]
    assert plan is not None
    plan_text = "\n".join(
        f"{step.order}. {step.objective} (tool: {step.tool})" for step in plan.steps
    )
    return [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=(
                f"Investigate SEC Form 4 filing {state['accession_number']}.\n\nPlan:\n{plan_text}"
            )
        ),
    ]


def build_investigate_node(
    investigator: Investigator, system_prompt: str
) -> Callable[[SurveillanceState], dict[str, object]]:
    def investigate_node(state: SurveillanceState) -> dict[str, object]:
        seed = [] if state["messages"] else _seed_messages(state, system_prompt)
        conversation = [*state["messages"], *seed]
        response = investigator.invoke(conversation)
        return {"messages": [*seed, response]}

    return investigate_node
