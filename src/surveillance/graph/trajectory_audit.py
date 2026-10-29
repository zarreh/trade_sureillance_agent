"""Deterministic audit of how an investigation reached its finding.

Pure: no I/O, no model call. Checks evidence coverage, call ordering,
citation validity and stated exemptions against what the tools actually
returned. The grounding judge (an LLM) decides whether a claim is *supported*;
this audit only decides whether the process behind it was sound
(docs/architecture/decisions/D-A2-7).
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from surveillance.graph.evidence import derive_exculpatory_factors
from surveillance.graph.nodes.check_plan import MANDATORY_TOOLS
from surveillance.schemas.finding import (
    ClaimedExemption,
    ExculpatoryKind,
    ProcessAudit,
    ToolCallRecord,
)
from surveillance.schemas.grounding import Claim

# `below_all_thresholds` says nothing about blackout or filing-lag violations,
# so it is never an exemption (same rule as evals/oracle.py).
TRUE_EXEMPTIONS: frozenset[ExculpatoryKind] = frozenset(
    {"reported_under_10b5_1", "tax_withholding", "option_exercise"}
)

_EXEMPTION_PATTERNS: dict[ExculpatoryKind, re.Pattern[str]] = {
    "reported_under_10b5_1": re.compile(r"10b5-?1", re.IGNORECASE),
    "tax_withholding": re.compile(r"tax[- ]withh\w+|withh\w+ (?:for|of) tax", re.IGNORECASE),
    "option_exercise": re.compile(
        r"option exercise|exercise of (?:an? |the )?\w*\s*options?", re.I
    ),
}
_NEGATION = re.compile(
    r"\b(?:not|no|nor|neither|never|without|cannot|unknown|absence|absent|unestablished)\b|n't",
    re.IGNORECASE,
)
# Clause boundaries, so "not under a 10b5-1 plan, but a tax withholding" splits.
_CLAUSE_SPLIT = re.compile(r"[.;:,\n]|\b(?:but|however|although|though|while)\b", re.IGNORECASE)


def extract_claimed_exemptions(claims: Sequence[Claim]) -> list[ClaimedExemption]:
    """Exemptions the claims assert. A clause containing a negation is skipped,
    which under-detects ("although unproven, this was a 10b5-1 sale") rather
    than flagging "no 10b5-1 plan was reported" as a claim."""
    found: list[ExculpatoryKind] = []
    for claim in claims:
        for clause in _CLAUSE_SPLIT.split(claim.text):
            if _NEGATION.search(clause):
                continue
            for kind, pattern in _EXEMPTION_PATTERNS.items():
                if pattern.search(clause) and kind not in found:
                    found.append(kind)
    return [ClaimedExemption(kind=kind) for kind in found]


def audit_trajectory(
    records: list[ToolCallRecord],
    claims: Sequence[Claim],
    claimed_exemptions: Sequence[ClaimedExemption],
) -> ProcessAudit:
    called_names = {r.tool_name for r in records}
    called = [t for t in MANDATORY_TOOLS if t in called_names]
    missing = [t for t in MANDATORY_TOOLS if t not in called_names]
    coverage = len(called) / len(MANDATORY_TOOLS)
    details_first = bool(records) and records[0].tool_name == "get_transaction_details"

    real_ids = {r.tool_call_id for r in records}
    cited = [cid for claim in claims for cid in claim.cited_tool_call_ids]
    fabricated = list(dict.fromkeys(cid for cid in cited if cid not in real_ids))
    # No claims means nothing is traceable, so an empty set scores 0, not vacuously 1.
    if fabricated or not claims:
        citation_validity = 0.0
    else:
        with_valid_id = sum(1 for c in claims if any(i in real_ids for i in c.cited_tool_call_ids))
        citation_validity = with_valid_id / len(claims)

    exemptions = [e for e in claimed_exemptions if e.kind in TRUE_EXEMPTIONS]
    derived = {(f.kind, f.applies_to_transaction_sk) for f in derive_exculpatory_factors(records)}
    derived_kinds = {kind for kind, _ in derived}
    # An exemption naming a transaction must hold for that line, not just somewhere in the filing.
    unsupported = [
        e
        for e in exemptions
        if (e.kind not in derived_kinds)
        or (e.transaction_sk is not None and (e.kind, e.transaction_sk) not in derived)
    ]
    exemption_validity = 0.0 if unsupported else 1.0

    ordering_factor = 1.0 if details_first else 0.5
    return ProcessAudit(
        mandatory_tools_called=called,
        mandatory_tools_missing=missing,
        coverage=coverage,
        details_first=details_first,
        fabricated_citation_ids=fabricated,
        citation_validity=citation_validity,
        claimed_exemptions=exemptions,
        unsupported_exemptions=unsupported,
        exemption_validity=exemption_validity,
        trajectory_score=coverage * ordering_factor * citation_validity * exemption_validity,
    )
