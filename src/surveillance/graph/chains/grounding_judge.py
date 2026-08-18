"""Pure LCEL runnable: scores each extracted claim against the recorded tool
evidence (docs/PLAN.md §5.1). Runs on the `reasoning` profile — this is the
judgement the finding is graded on (§5.4). Aggregation (`unsupported` count,
`confidence`) is deterministic and lives in `nodes/judge_grounding.py`, not
in this chain's output.
"""

from __future__ import annotations

from typing import cast

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from surveillance.graph.protocols import GroundingJudgeChain
from surveillance.prompts.loader import load_prompt
from surveillance.schemas.grounding import ClaimJudgments


def build_grounding_judge_chain(model: BaseChatModel) -> GroundingJudgeChain:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", load_prompt("grounding_judge_v1")),
            ("human", "Claims:\n{claims}\n\nEvidence (tool results):\n{evidence}"),
        ]
    )
    return cast(GroundingJudgeChain, prompt | model.with_structured_output(ClaimJudgments))
