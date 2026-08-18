"""Pure LCEL runnable: writes the draft finding from the investigation
conversation. Exculpatory factors are attached later, deterministically, in
`graph/evidence.py` — never part of this chain's output.
"""

from __future__ import annotations

from typing import cast

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from surveillance.graph.protocols import FindingWriterChain
from surveillance.prompts.loader import load_prompt
from surveillance.schemas.finding import ComplianceFindingDraft


def build_finding_writer_chain(model: BaseChatModel) -> FindingWriterChain:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", load_prompt("finding_writer_v1")),
            MessagesPlaceholder("messages"),
        ]
    )
    # with_structured_output's stub return type is broader than the concrete
    # Pydantic model it actually produces at runtime.
    return cast(FindingWriterChain, prompt | model.with_structured_output(ComplianceFindingDraft))
