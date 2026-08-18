"""Pure LCEL runnable: turns an accession number (plus optional replan
feedback) into an investigation plan. No knowledge that a graph exists.
"""

from __future__ import annotations

from typing import cast

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from surveillance.graph.protocols import PlannerChain
from surveillance.prompts.loader import load_prompt
from surveillance.schemas.plan import InvestigationPlan


def build_planner_chain(model: BaseChatModel) -> PlannerChain:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", load_prompt("planner_v1")),
            (
                "human",
                "Transaction to investigate: {accession_number}\n\n"
                "Feedback on a previous plan, if any: {feedback}",
            ),
        ]
    )
    # with_structured_output's stub return type is broader than the concrete
    # Pydantic model it actually produces at runtime.
    return cast(PlannerChain, prompt | model.with_structured_output(InvestigationPlan))
