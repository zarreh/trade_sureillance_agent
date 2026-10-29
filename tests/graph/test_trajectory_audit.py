import json

from surveillance.graph.nodes.check_plan import MANDATORY_TOOLS
from surveillance.graph.trajectory_audit import audit_trajectory, extract_claimed_exemptions
from surveillance.schemas.finding import ClaimedExemption, ToolCallRecord
from surveillance.schemas.grounding import Claim


def _details(code: str = "S", sk: int = 1, plan: str = "false") -> str:
    return json.dumps(
        {
            "reported_under_10b5_1": plan,
            "transactions": [{"nonderiv_trans_sk": sk, "trans_code": code, "trans_value": 10.0}],
        }
    )


def _records(
    tools: tuple[str, ...] = MANDATORY_TOOLS, details: str | None = None
) -> list[ToolCallRecord]:
    return [
        ToolCallRecord(
            tool_call_id=f"t{i}",
            tool_name=name,
            args={},
            result=(details or _details()) if name == "get_transaction_details" else "{}",
        )
        for i, name in enumerate(tools, start=1)
    ]


def _claim(*ids: str, text: str = "a claim") -> Claim:
    return Claim(id="c1", text=text, cited_tool_call_ids=list(ids))


def test_full_clean_run_scores_one() -> None:
    audit = audit_trajectory(_records(), [_claim("t1")], [])
    assert audit.coverage == 1.0
    assert audit.mandatory_tools_missing == []
    assert audit.details_first
    assert audit.citation_validity == 1.0
    assert audit.exemption_validity == 1.0
    assert audit.trajectory_score == 1.0


def test_missing_tools_are_named_and_reduce_coverage() -> None:
    audit = audit_trajectory(_records(MANDATORY_TOOLS[:3]), [_claim("t1")], [])
    assert audit.mandatory_tools_called == list(MANDATORY_TOOLS[:3])
    assert audit.mandatory_tools_missing == list(MANDATORY_TOOLS[3:])
    assert audit.coverage == 0.5


def test_details_not_first_halves_the_score() -> None:
    reordered = (*MANDATORY_TOOLS[1:], MANDATORY_TOOLS[0])
    audit = audit_trajectory(_records(reordered), [_claim("t6")], [])
    assert not audit.details_first
    assert audit.trajectory_score == 0.5


def test_no_calls_means_zero_coverage_and_not_details_first() -> None:
    audit = audit_trajectory([], [_claim()], [])
    assert audit.coverage == 0.0
    assert not audit.details_first
    assert audit.trajectory_score == 0.0


def test_fabricated_citation_zeroes_validity() -> None:
    audit = audit_trajectory(_records(), [_claim("t1", "ghost"), _claim("t2")], [])
    assert audit.fabricated_citation_ids == ["ghost"]
    assert audit.citation_validity == 0.0
    assert audit.trajectory_score == 0.0


def test_citation_validity_is_fraction_of_claims_with_a_valid_id() -> None:
    claims = [_claim("t1"), _claim(), _claim("t2"), _claim()]
    audit = audit_trajectory(_records(), claims, [])
    assert audit.fabricated_citation_ids == []
    assert audit.citation_validity == 0.5


def test_no_claims_is_not_vacuously_valid() -> None:
    assert audit_trajectory(_records(), [], []).citation_validity == 0.0


def test_supported_exemption_passes() -> None:
    records = _records(details=_details(plan="true"))
    audit = audit_trajectory(
        records, [_claim("t1")], [ClaimedExemption(kind="reported_under_10b5_1")]
    )
    assert audit.unsupported_exemptions == []
    assert audit.exemption_validity == 1.0


def test_unsupported_exemption_zeroes_validity() -> None:
    claimed = [ClaimedExemption(kind="reported_under_10b5_1")]
    audit = audit_trajectory(_records(), [_claim("t1")], claimed)
    assert audit.unsupported_exemptions == claimed
    assert audit.exemption_validity == 0.0
    assert audit.trajectory_score == 0.0


def test_below_all_thresholds_is_never_an_exemption() -> None:
    audit = audit_trajectory(
        _records(), [_claim("t1")], [ClaimedExemption(kind="below_all_thresholds")]
    )
    assert audit.claimed_exemptions == []
    assert audit.exemption_validity == 1.0


def test_tax_withholding_on_one_line_does_not_support_another_line() -> None:
    # Canonical case 7: an F line must not clear an unrelated S line.
    details = json.dumps(
        {
            "reported_under_10b5_1": "false",
            "transactions": [
                {"nonderiv_trans_sk": 1, "trans_code": "F", "trans_value": 10.0},
                {"nonderiv_trans_sk": 2, "trans_code": "S", "trans_value": 10.0},
            ],
        }
    )
    records = _records(details=details)
    on_f = audit_trajectory(
        records, [_claim("t1")], [ClaimedExemption(kind="tax_withholding", transaction_sk=1)]
    )
    on_s = audit_trajectory(
        records, [_claim("t1")], [ClaimedExemption(kind="tax_withholding", transaction_sk=2)]
    )
    assert on_f.exemption_validity == 1.0
    assert on_s.unsupported_exemptions == [
        ClaimedExemption(kind="tax_withholding", transaction_sk=2)
    ]


def test_extract_claimed_exemptions_reads_each_kind() -> None:
    claims = [
        _claim(text="The sale was made under a 10b5-1 plan."),
        _claim(text="Shares were withheld for tax withholding on vesting."),
        _claim(text="This was an option exercise."),
    ]
    kinds = [e.kind for e in extract_claimed_exemptions(claims)]
    assert kinds == ["reported_under_10b5_1", "tax_withholding", "option_exercise"]


def test_extract_claimed_exemptions_skips_negated_mentions() -> None:
    claims = [
        _claim(text="No 10b5-1 plan was reported."),
        _claim(text="The 10b5-1 status is unknown."),
        _claim(text="This was not a tax withholding, but an open-market sale."),
    ]
    assert extract_claimed_exemptions(claims) == []


def test_extract_claimed_exemptions_deduplicates() -> None:
    claims = [_claim(text="Reported under a 10b5-1 plan."), _claim(text="A 10b5-1 sale.")]
    assert len(extract_claimed_exemptions(claims)) == 1
