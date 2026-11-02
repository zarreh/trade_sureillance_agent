"""Pure LCEL runnable: decomposes the draft finding's `finding_text` into
discrete, tool_call_id-cited claims (docs/PLAN.md §5.1). Runs on the `fast`
profile — this is extraction, not judgement (§5.4).
"""

from __future__ import annotations

from typing import cast

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from surveillance.graph.protocols import ClaimExtractorChain
from surveillance.prompts.loader import load_prompt
from surveillance.schemas.grounding import ExtractedClaims


def build_claim_extractor_chain(model: BaseChatModel) -> ClaimExtractorChain:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", load_prompt("claim_extractor_v2")),
            (
                "human",
                "Finding text:\n{finding_text}\n\n"
                "Evidence index (tool_call_id: tool(args) -> result excerpt):\n{evidence_index}",
            ),
        ]
    )
    return cast(ClaimExtractorChain, prompt | model.with_structured_output(ExtractedClaims))
