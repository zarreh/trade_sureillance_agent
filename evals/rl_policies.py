"""Scripted policies for the surveillance environment (docs/architecture/decisions/D-A2-8).

`reference` investigates properly. Every other policy is a deliberate shortcut
or gaming strategy that the reward must score well below it. A policy sees only
the environment's observations; the "label" policies are additionally handed the
answer key on purpose, to show that a right answer alone is not rewarded.
"""

from __future__ import annotations

import json
from typing import Any, Protocol

from data.scenarios import SCENARIOS
from evals.oracle import Disposition, decide, next_tool_call
from surveillance.graph.evidence import derive_exculpatory_factors
from surveillance.graph.trajectory_audit import TRUE_EXEMPTIONS
from surveillance.schemas.finding import ToolCallRecord

ANSWER_KEY: dict[str, Disposition] = {s.accession_number: s.expected_disposition for s in SCENARIOS}


class Policy(Protocol):
    name: str
    description: str

    def begin(self, observation: str) -> None: ...

    def act(self, observation: str) -> str: ...


def _tool_call(name: str, args: dict[str, object]) -> str:
    return json.dumps({"type": "tool_call", "name": name, "args": args})


def _submit(
    disposition: str,
    text: str,
    cited: list[str],
    exemptions: list[dict[str, Any]] | None = None,
) -> str:
    return json.dumps(
        {
            "type": "submit",
            "disposition": disposition,
            "claims": [{"text": text, "cited_tool_call_ids": cited}],
            "exemptions": exemptions or [],
        }
    )


class _Gatherer:
    """Tracks the episode and gathers the mandatory evidence, then hands the
    final submission to `_submission`. Subclasses change only how it submits."""

    name = ""
    description = ""

    def __init__(self) -> None:
        self._accession = ""
        self._records: list[ToolCallRecord] = []
        self._pending: tuple[str, dict[str, object]] | None = None

    def begin(self, observation: str) -> None:
        self._accession = json.loads(observation)["accession_number"]
        self._records = []
        self._pending = None

    def _observe(self, observation: str) -> None:
        payload = json.loads(observation)
        if self._pending is not None and "tool_call_id" in payload:
            name, args = self._pending
            self._records.append(
                ToolCallRecord(
                    tool_call_id=payload["tool_call_id"],
                    tool_name=name,
                    args=args,
                    result=json.dumps(payload["result"]),
                )
            )
        self._pending = None

    def act(self, observation: str) -> str:
        self._observe(observation)
        call = next_tool_call(self._accession, self._records)
        if call is None:
            return self._submission(self._records)
        self._pending = call
        return _tool_call(*call)

    def _submission(self, records: list[ToolCallRecord]) -> str:
        raise NotImplementedError

    def _ids(self, records: list[ToolCallRecord]) -> list[str]:
        return [r.tool_call_id for r in records]


class ReferencePolicy(_Gatherer):
    name = "reference"
    description = "Gathers all six tools, decides with the oracle, claims only derived exemptions."

    def _submission(self, records: list[ToolCallRecord]) -> str:
        decision = decide(records)
        if decision is None:
            return _submit("escalate", "No transaction details could be retrieved.", [])
        exemptions = [
            {"kind": f.kind, "transaction_sk": f.applies_to_transaction_sk}
            for f in derive_exculpatory_factors(records)
            if f.kind in TRUE_EXEMPTIONS
        ]
        return _submit(decision.disposition, decision.reason, self._ids(records), exemptions)


class FixedDispositionPolicy(_Gatherer):
    """One disposition for every case. With `gather=False` it skips all evidence."""

    def __init__(self, disposition: Disposition, description: str, gather: bool = True) -> None:
        super().__init__()
        self.name = f"always_{disposition}" if gather else f"blind_always_{disposition}"
        self.description = description
        self._disposition = disposition
        self._gather = gather

    def act(self, observation: str) -> str:
        if self._gather:
            return super().act(observation)
        return self._submission([])

    def _submission(self, records: list[ToolCallRecord]) -> str:
        return _submit(self._disposition, "Fixed disposition.", self._ids(records))


class NoEvidenceGuesser:
    name = "no_evidence_guesser"
    description = "Handed the correct label, calls no tools, submits it."

    def __init__(self) -> None:
        self._accession = ""

    def begin(self, observation: str) -> None:
        self._accession = json.loads(observation)["accession_number"]

    def act(self, observation: str) -> str:
        return _submit(ANSWER_KEY[self._accession], "Answered without investigating.", [])


class CitationFabricator(_Gatherer):
    name = "citation_fabricator"
    description = (
        "Correct label after real evidence, but also cites a tool-call id that never existed."
    )

    def _submission(self, records: list[ToolCallRecord]) -> str:
        cited = [*self._ids(records)[:1], "ghost-1"]
        return _submit(ANSWER_KEY[self._accession], "Cited evidence.", cited)


class ExemptionClaimer(_Gatherer):
    name = "exemption_claimer"
    description = "Correct label and real citations, but always claims a 10b5-1 exemption."

    def _submission(self, records: list[ToolCallRecord]) -> str:
        return _submit(
            ANSWER_KEY[self._accession],
            "Resolved.",
            self._ids(records),
            [{"kind": "reported_under_10b5_1"}],
        )


class ToolSpammer:
    name = "tool_spammer"
    description = "Calls a tool over and over until the budget ends."

    def begin(self, observation: str) -> None:
        pass

    def act(self, observation: str) -> str:
        return _tool_call("get_compliance_rules", {})


def build_policies() -> list[Policy]:
    return [
        ReferencePolicy(),
        FixedDispositionPolicy("flag", "Always flags: the outcome-only winner on flag recall."),
        FixedDispositionPolicy("escalate", "Always escalates: over-alerting."),
        FixedDispositionPolicy("clear", "Always clears: missing violations."),
        FixedDispositionPolicy(
            "clear",
            "Skips all evidence and always clears: wrong answers with no investigation.",
            gather=False,
        ),
        NoEvidenceGuesser(),
        CitationFabricator(),
        ExemptionClaimer(),
        ToolSpammer(),
    ]
