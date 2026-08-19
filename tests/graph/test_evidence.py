from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from data.build_store import build_facts_db
from data.generate_compliance_db import build_policy_db
from surveillance.graph.evidence import (
    derive_exculpatory_factors,
    derive_reported_under_10b5_1,
    extract_tool_call_records,
)
from surveillance.store.fact_store import FactStore
from surveillance.store.policy_store import PolicyStore
from surveillance.tools.get_applicable_role_limits import build_get_applicable_role_limits_tool
from surveillance.tools.get_transaction_details import build_get_transaction_details_tool

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "edgar_sample"


@pytest.fixture
def stores(tmp_path: Path) -> tuple[FactStore, PolicyStore]:
    facts_path = tmp_path / "facts.db"
    policy_path = tmp_path / "policy.db"
    build_facts_db(FIXTURE_DIR, facts_path)
    build_policy_db(policy_path)
    return FactStore(facts_path), PolicyStore(policy_path)


def _conversation_for(
    accession_number: str, stores: tuple[FactStore, PolicyStore]
) -> list[BaseMessage]:
    fact_store, policy_store = stores
    details_tool = build_get_transaction_details_tool(fact_store)
    role_limits_tool = build_get_applicable_role_limits_tool(policy_store)
    details_result = details_tool.invoke({"accession_number": accession_number})
    role_limits_result = role_limits_tool.invoke({"relationship": "Officer", "title": None})
    return [
        AIMessage(
            content="",
            tool_calls=[
                {"name": "get_transaction_details", "args": {}, "id": "call_details"},
                {"name": "get_applicable_role_limits", "args": {}, "id": "call_limits"},
            ],
        ),
        ToolMessage(content=details_result, tool_call_id="call_details"),
        ToolMessage(content=role_limits_result, tool_call_id="call_limits"),
    ]


def test_extract_tool_call_records_pairs_calls_with_results(
    stores: tuple[FactStore, PolicyStore],
) -> None:
    conversation = _conversation_for("0000000001-25-000001", stores)
    records = extract_tool_call_records(conversation)
    assert len(records) == 2
    assert {r.tool_name for r in records} == {
        "get_transaction_details",
        "get_applicable_role_limits",
    }


def test_10b5_1_and_low_value_produce_exculpatory_factors(
    stores: tuple[FactStore, PolicyStore],
) -> None:
    # Accession 1: Officer/CEO, 10b5_1=true, value 3000*150.25=450750 (well under the
    # Executive single-trade limit).
    conversation = _conversation_for("0000000001-25-000001", stores)
    records = extract_tool_call_records(conversation)
    factors = derive_exculpatory_factors(records)
    kinds = {f.kind for f in factors}
    assert "reported_under_10b5_1" in kinds
    assert "below_all_thresholds" in kinds
    assert all(f.evidence_tool_call_id in {"call_details", "call_limits"} for f in factors)


def test_tax_withholding_produces_exemption(stores: tuple[FactStore, PolicyStore]) -> None:
    conversation = _conversation_for("0000000001-25-000002", stores)  # Code F
    records = extract_tool_call_records(conversation)
    factors = derive_exculpatory_factors(records)
    assert any(f.kind == "tax_withholding" for f in factors)


def test_missing_transaction_details_yields_no_factors() -> None:
    assert derive_exculpatory_factors([]) == []


def test_derive_reported_under_10b5_1_reads_the_filing_level_tri_state(
    stores: tuple[FactStore, PolicyStore],
) -> None:
    conversation = _conversation_for("0000000001-25-000001", stores)  # 10b5_1=true
    records = extract_tool_call_records(conversation)
    assert derive_reported_under_10b5_1(records) == "true"


def test_derive_reported_under_10b5_1_defaults_to_unknown_with_no_evidence() -> None:
    assert derive_reported_under_10b5_1([]) == "unknown"
