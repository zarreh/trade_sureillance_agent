"""Structural (Protocol) types for the LLM-backed pieces nodes depend on.

Node factories accept these instead of concrete `Runnable[...]` types so a
plain test double (with just a matching `.invoke()`) can stand in without
subclassing LangChain's `Runnable` — real chains satisfy them structurally too.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from langchain_core.messages import BaseMessage

from surveillance.schemas.finding import ComplianceFindingDraft
from surveillance.schemas.plan import InvestigationPlan


class PlannerChain(Protocol):
    def invoke(self, input: dict[str, str]) -> InvestigationPlan: ...


class FindingWriterChain(Protocol):
    def invoke(self, input: dict[str, object]) -> ComplianceFindingDraft: ...


class Investigator(Protocol):
    def invoke(self, messages: Sequence[BaseMessage]) -> BaseMessage: ...
