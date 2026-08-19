"""A deterministic, rules-based stand-in for the live LLM chains — used
because no LLM API key is available in this environment (docs/PLAN.md §7
Phase 7). This is NOT a claim about model quality: it is a reference
decision function, applying the same objective rule thresholds a compliance
officer would check, so Layer 1 exercises the real graph plumbing (planning,
tool wiring, evidence derivation, the grounding loop, publication) against a
known-correct oracle rather than recorded model transcripts, which this
environment cannot capture. Replace this with real recorded responses
(`evals/record_responses.py`, not yet written) once a live LLM is available.

Deliberately excludes `below_all_thresholds` from the set of dispositions
that clear a line: being under the dollar thresholds says nothing about a
blackout-window or late-filing violation, so it must not suppress those.
Only `reported_under_10b5_1`, `tax_withholding`, and `option_exercise` are
genuine procedural exemptions.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Literal

from langchain_core.messages import AIMessage, BaseMessage

from surveillance.graph.evidence import derive_exculpatory_factors, extract_tool_call_records
from surveillance.graph.nodes.check_plan import MANDATORY_TOOLS
from surveillance.schemas.finding import ComplianceFindingDraft, ToolCallRecord
from surveillance.schemas.grounding import Claim, ClaimJudgment, ClaimJudgments, ExtractedClaims
from surveillance.schemas.plan import InvestigationPlan, PlanStep

Disposition = Literal["clear", "flag", "escalate"]

_VOLUME_SPIKE_SHARE_THRESHOLD = 150_000
_SEVERITY_RANK: dict[Disposition, int] = {"clear": 0, "flag": 1, "escalate": 2}
_TRUE_EXEMPTIONS = {"reported_under_10b5_1", "tax_withholding", "option_exercise"}


def _latest_json(records: list[ToolCallRecord], tool_name: str) -> dict[str, object] | None:
    matches = [r for r in records if r.tool_name == tool_name]
    if not matches:
        return None
    try:
        parsed = json.loads(matches[-1].result)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _focal_trans_date(details: dict[str, object]) -> str:
    lines = details.get("transactions")
    assert isinstance(lines, list)
    for line in lines:
        if not line.get("superseded"):
            return str(line["trans_date"])
    return str(lines[0]["trans_date"])


class OraclePlannerChain:
    """Always plans the full mandatory tool set, get_transaction_details first."""

    def invoke(self, _: dict[str, str]) -> InvestigationPlan:
        steps = [
            PlanStep(order=i, objective=f"gather {name}", tool=name, why="required evidence")
            for i, name in enumerate(MANDATORY_TOOLS, start=1)
        ]
        return InvestigationPlan(steps=steps)


class OracleInvestigator:
    """Deterministically gathers all six mandatory tools, deriving each
    call's arguments from the real result of `get_transaction_details` —
    never from the scenario definition itself."""

    def __init__(self, accession_number: str) -> None:
        self._accession_number = accession_number

    def invoke(self, conversation: Sequence[BaseMessage]) -> AIMessage:
        records = extract_tool_call_records(conversation)
        called = {r.tool_name for r in records}
        remaining = [name for name in MANDATORY_TOOLS if name not in called]
        if not remaining:
            return AIMessage(content="Investigation complete.")

        next_tool = remaining[0]
        if next_tool == "get_transaction_details":
            args: dict[str, object] = {"accession_number": self._accession_number}
        else:
            details = _latest_json(records, "get_transaction_details")
            if details is None:
                return AIMessage(content="Investigation complete.")
            if next_tool == "get_applicable_role_limits":
                args = {
                    "relationship": details["rptowner_relationship"],
                    "title": details["rptowner_title"] or None,
                }
            elif next_tool == "get_compliance_rules":
                args = {}
            elif next_tool in ("rolling_90d_trading_volume", "insider_trading_baseline"):
                args = {
                    "rptowner_cik": details["rptowner_cik"],
                    "as_of_date": _focal_trans_date(details),
                }
            else:  # get_material_events
                args = {
                    "issuer_cik": details["issuer_cik"],
                    "on_date": _focal_trans_date(details),
                }

        return AIMessage(
            content="", tool_calls=[{"name": next_tool, "args": args, "id": f"call_{next_tool}"}]
        )


def _line_verdict(
    line: dict[str, object],
    details: dict[str, object],
    role_limits: dict[str, object] | None,
    rolling_90d: dict[str, object] | None,
    baseline: dict[str, object] | None,
    material_event: dict[str, object] | None,
    exempt_sks: set[int],
) -> tuple[Disposition, str]:
    sk = line["nonderiv_trans_sk"]
    if line.get("superseded"):
        return "clear", "superseded, excluded from the active record"
    if sk in exempt_sks:
        return "clear", "exempted by a per-transaction exculpatory factor"

    trans_value = line["trans_value"]
    assert isinstance(trans_value, int | float)

    if role_limits is not None and trans_value > role_limits["single_trade_limit"]:  # type: ignore[operator]
        return "escalate", "single trade value exceeds the applicable single-trade limit"
    if (
        role_limits is not None
        and rolling_90d is not None
        and rolling_90d.get("total_volume", 0) > role_limits["rolling_90d_limit"]  # type: ignore[operator]
    ):
        return "flag", "rolling 90-day volume exceeds the applicable limit"
    if material_event is not None and material_event.get("in_blackout"):
        return "flag", "transaction date falls within a material-event blackout window"
    filing_lag = details.get("filing_lag_trading_days")
    if isinstance(filing_lag, int) and filing_lag > 2:
        return "flag", "Section 16(a) filing lag exceeds 2 trading days"
    if (
        baseline is not None
        and baseline.get("transaction_count", 0) == 0
        and line["trans_shares"] > _VOLUME_SPIKE_SHARE_THRESHOLD  # type: ignore[operator]
    ):
        return "flag", "unusual share volume with no established trailing baseline"
    return "clear", "within all applicable limits"


class OracleFindingWriterChain:
    def invoke(self, input_: dict[str, object]) -> ComplianceFindingDraft:
        messages = input_["messages"]
        assert isinstance(messages, Sequence)
        records = extract_tool_call_records(messages)
        details = _latest_json(records, "get_transaction_details")
        role_limits = _latest_json(records, "get_applicable_role_limits")
        rolling_90d = _latest_json(records, "rolling_90d_trading_volume")
        baseline = _latest_json(records, "insider_trading_baseline")
        material_event = _latest_json(records, "get_material_events")
        exempt_sks = {
            f.applies_to_transaction_sk
            for f in derive_exculpatory_factors(records)
            if f.kind in _TRUE_EXEMPTIONS
        }

        if details is None:
            return ComplianceFindingDraft(
                disposition="escalate",
                severity="High",
                confidence="low",
                finding_text="No transaction details could be retrieved for this filing.",
            )

        lines = details.get("transactions", [])
        assert isinstance(lines, list)
        verdicts = [
            _line_verdict(
                line, details, role_limits, rolling_90d, baseline, material_event, exempt_sks
            )
            for line in lines
        ]
        disposition, reason = max(verdicts, key=lambda v: _SEVERITY_RANK[v[0]])
        severity: Literal["Low", "Medium", "High", "Critical"] | None = {
            "clear": None,
            "flag": "Medium",
            "escalate": "High",
        }[disposition]
        accession = details.get("accession_number", "unknown")
        return ComplianceFindingDraft(
            disposition=disposition,
            severity=severity,
            confidence="high",
            finding_text=f"{reason} (accession {accession}).",
        )


class OracleClaimExtractorChain:
    """Coarse but honest: one claim covering the finding text, citing every
    tool_call_id actually gathered — real claim decomposition quality is an
    LLM-judgment question this scripted oracle cannot stand in for."""

    def invoke(self, input_: dict[str, object]) -> ExtractedClaims:
        finding_text = input_.get("finding_text", "")
        tool_call_ids = input_.get("tool_call_ids", [])
        assert isinstance(tool_call_ids, list)
        return ExtractedClaims(
            claims=[Claim(id="c1", text=str(finding_text), cited_tool_call_ids=list(tool_call_ids))]
        )


class OracleGroundingJudgeChain:
    """Claims here are always built from real tool_call_ids gathered during
    the investigation (never invented), so they are supported whenever at
    least one citation exists."""

    def invoke(self, input_: dict[str, object]) -> ClaimJudgments:
        claims = input_.get("claims", [])
        assert isinstance(claims, list)
        judgments = [
            ClaimJudgment(
                claim_id=c["id"],
                supported=bool(c.get("cited_tool_call_ids")),
                reason=(
                    "cited real tool_call_ids gathered during the investigation"
                    if c.get("cited_tool_call_ids")
                    else "no tool_call_id cited"
                ),
            )
            for c in claims
        ]
        return ClaimJudgments(judgments=judgments)
