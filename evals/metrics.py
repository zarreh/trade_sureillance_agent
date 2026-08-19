"""Metric definitions, fixed before labelling (docs/PLAN.md §4.5) — shared by
both evaluation layers so Layer 1 (canonical, n=10, gates PR CI) and Layer 2
(stratified, hand-labelled, scheduled) report the exact same numbers the same
way. A metric is defined once, here, never re-derived ad hoc per report.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Disposition = Literal["clear", "flag", "escalate"]

_POSITIVE = {"flag", "escalate"}


@dataclass(frozen=True)
class EvalResult:
    """One investigation's outcome, scored against its expected label."""

    scenario_id: str
    expected_disposition: Disposition
    actual_disposition: Disposition
    plan_ok: bool
    total_claims: int
    claims_with_citation: int
    unsupported_claims: int
    cost_usd: float
    latency_seconds: float


@dataclass(frozen=True)
class MetricsReport:
    n: int
    disposition_accuracy: float
    flag_precision: float
    flag_recall: float
    severity_miss_rate: float
    false_positive_rate_on_clear: float
    citation_coverage_pct: float
    unsupported_claim_rate: float
    tool_call_accuracy: float
    cost_per_investigation_usd: float
    latency_p50_seconds: float
    latency_p95_seconds: float


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = round(p * (len(ordered) - 1))
    return ordered[index]


def _rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def compute_metrics(results: list[EvalResult]) -> MetricsReport:
    n = len(results)
    if n == 0:
        raise ValueError("compute_metrics requires at least one result")

    exact_matches = sum(1 for r in results if r.actual_disposition == r.expected_disposition)

    true_positives = sum(
        1
        for r in results
        if r.expected_disposition in _POSITIVE and r.actual_disposition in _POSITIVE
    )
    predicted_positive = sum(1 for r in results if r.actual_disposition in _POSITIVE)
    actual_positive = sum(1 for r in results if r.expected_disposition in _POSITIVE)

    # A severity miss is flag-where-escalate or escalate-where-flag — both
    # sides agree something was wrong, they disagree how seriously
    # (docs/PLAN.md §4.5) — never counted as a false positive.
    severity_misses = sum(
        1
        for r in results
        if r.expected_disposition in _POSITIVE
        and r.actual_disposition in _POSITIVE
        and r.actual_disposition != r.expected_disposition
    )
    expected_clear = sum(1 for r in results if r.expected_disposition == "clear")
    false_positives_on_clear = sum(
        1 for r in results if r.expected_disposition == "clear" and r.actual_disposition != "clear"
    )

    total_claims = sum(r.total_claims for r in results)
    claims_with_citation = sum(r.claims_with_citation for r in results)
    unsupported_claims = sum(r.unsupported_claims for r in results)

    return MetricsReport(
        n=n,
        disposition_accuracy=_rate(exact_matches, n),
        flag_precision=_rate(true_positives, predicted_positive),
        flag_recall=_rate(true_positives, actual_positive),
        severity_miss_rate=_rate(severity_misses, actual_positive),
        false_positive_rate_on_clear=_rate(false_positives_on_clear, expected_clear),
        citation_coverage_pct=100.0 * _rate(claims_with_citation, total_claims),
        unsupported_claim_rate=_rate(unsupported_claims, total_claims),
        tool_call_accuracy=_rate(sum(1 for r in results if r.plan_ok), n),
        cost_per_investigation_usd=sum(r.cost_usd for r in results) / n,
        latency_p50_seconds=_percentile([r.latency_seconds for r in results], 0.50),
        latency_p95_seconds=_percentile([r.latency_seconds for r in results], 0.95),
    )
