"""A model + a tool set + a prompt id, nothing else (docs/PLAN.md §9.3).

The system prompt is injected once by `nodes/investigate.py` when the ReAct
loop begins — this module just binds the tools to the model.
"""

from __future__ import annotations

from typing import cast

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import StructuredTool

from surveillance.graph.protocols import Investigator


def build_investigator(model: BaseChatModel, tools: list[StructuredTool]) -> Investigator:
    return cast(Investigator, model.bind_tools(tools))
