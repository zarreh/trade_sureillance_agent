"""Derives typed evidence directly from the message history.

Two responsibilities, both deterministic — never authored by the model
(don't spend a model call on a decision an `if` can make, docs/PLAN.md D-A2-3):
turning the raw tool-call/tool-result message pairs into a typed log, and
deriving exculpatory factors from that log's `get_transaction_details` result.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Literal

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from surveillance.schemas.finding import ExculpatoryFactor, ExculpatoryKind, ToolCallRecord

_EXEMPT_CODES: dict[str, ExculpatoryKind] = {"F": "tax_withholding", "M": "option_exercise"}


def extract_tool_call_records(messages: Sequence[BaseMessage]) -> list[ToolCallRecord]:
    """Pairs every AIMessage tool call with its ToolMessage result, in order."""
    results_by_id = {m.tool_call_id: m for m in messages if isinstance(m, ToolMessage)}
    records = []
    for message in messages:
        if not (isinstance(message, AIMessage) and message.tool_calls):
            continue
        for call in message.tool_calls:
            call_id = call["id"]
            if call_id is None:
                continue
            result = results_by_id.get(call_id)
            records.append(
                ToolCallRecord(
                    tool_call_id=call_id,
                    tool_name=call["name"],
                    args=call["args"],
                    result=str(result.content) if result else "",
                )
            )
    return records


def _latest(records: list[ToolCallRecord], tool_name: str) -> ToolCallRecord | None:
    matches = [r for r in records if r.tool_name == tool_name]
    return matches[-1] if matches else None


def derive_reported_under_10b5_1(
    records: list[ToolCallRecord],
) -> Literal["true", "false", "unknown"]:
    """The filing-level 10b5-1 tri-state, straight from `get_transaction_details`
    — never inferred from its absence. Surfaced on the finding so the UI can
    render `unknown` as "not established", never as "no plan" (docs/PLAN.md §3.4)."""
    details = _latest(records, "get_transaction_details")
    if details is None:
        return "unknown"
    try:
        payload = json.loads(details.result)
    except json.JSONDecodeError:
        return "unknown"
    value = payload.get("reported_under_10b5_1")
    return value if value in ("true", "false", "unknown") else "unknown"


def derive_exculpatory_factors(records: list[ToolCallRecord]) -> list[ExculpatoryFactor]:
    """Derives exculpatory factors from the actual tool results, not the LLM's
    narrative — so a claimed exemption is always traceable to a real tool call.

    `below_all_thresholds` compares only the single-trade limit per line; the
    rolling-90d and baseline comparisons are narrative (finding_text) territory
    until a later phase adds a second deterministic pass.
    """
    details = _latest(records, "get_transaction_details")
    role_limits = _latest(records, "get_applicable_role_limits")
    if details is None:
        return []

    try:
        details_payload = json.loads(details.result)
    except json.JSONDecodeError:
        return []
    if "error" in details_payload:
        return []

    single_trade_limit = None
    if role_limits is not None:
        try:
            single_trade_limit = json.loads(role_limits.result).get("single_trade_limit")
        except json.JSONDecodeError:
            single_trade_limit = None

    reported_10b5_1 = details_payload.get("reported_under_10b5_1")
    factors: list[ExculpatoryFactor] = []
    for line in details_payload.get("transactions", []):
        sk = line["nonderiv_trans_sk"]
        if reported_10b5_1 == "true":
            factors.append(
                ExculpatoryFactor(
                    kind="reported_under_10b5_1",
                    evidence_tool_call_id=details.tool_call_id,
                    applies_to_transaction_sk=sk,
                )
            )
        exempt_kind = _EXEMPT_CODES.get(line["trans_code"])
        if exempt_kind:
            factors.append(
                ExculpatoryFactor(
                    kind=exempt_kind,
                    evidence_tool_call_id=details.tool_call_id,
                    applies_to_transaction_sk=sk,
                )
            )
        if single_trade_limit is not None and line["trans_value"] < single_trade_limit:
            factors.append(
                ExculpatoryFactor(
                    kind="below_all_thresholds",
                    evidence_tool_call_id=role_limits.tool_call_id,  # type: ignore[union-attr]
                    applies_to_transaction_sk=sk,
                )
            )
    return factors
