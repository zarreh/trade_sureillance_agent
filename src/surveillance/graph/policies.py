"""Model selection per node — never inline in a node (docs/PLAN.md §5.4).

Phase 3 ships a single provider (OpenAI). The Gemini availability-fallback and
Ollama offline profile are scheduled (D-A2-4), not blocking: fallback belongs
here, engaged only on transport-level failure, never to paper over a schema
or tool-calling defect.
"""

from __future__ import annotations

import warnings

from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from surveillance.settings import Settings

# Streaming a structured-output call makes langchain-openai call `chunk.model_dump()`
# on an OpenAI parsed message whose `parsed` field is typed `None`. The output is
# correct; only the serializer warns (openai-python#2872). Scoped to that field.
warnings.filterwarnings(
    "ignore",
    message=r"(?s)Pydantic serializer warnings:.*field_name='parsed'",
    category=UserWarning,
    module=r"pydantic\.main",
)

FAST_MODEL = "gpt-4o-mini"
REASONING_MODEL = "gpt-4o"


def _api_key(settings: Settings) -> SecretStr | None:
    return SecretStr(settings.openai_api_key) if settings.openai_api_key else None


def build_fast_model(settings: Settings) -> ChatOpenAI:
    """Planner, investigator — cheap, high-volume reasoning."""
    return ChatOpenAI(model=FAST_MODEL, temperature=0, api_key=_api_key(settings))


def build_reasoning_model(settings: Settings) -> ChatOpenAI:
    """Finding writer — the model whose output is judged for grounding."""
    return ChatOpenAI(model=REASONING_MODEL, temperature=0, api_key=_api_key(settings))
