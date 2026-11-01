"""The claim extractor's rendered prompt, checked against a recorded live run
in which the extractor cited no tool-call ids at all (evals/recordings/)."""

import json
from pathlib import Path

from langchain_core.messages import messages_from_dict
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from surveillance.graph.chains.claim_extractor import build_claim_extractor_chain
from surveillance.graph.evidence import extract_tool_call_records, format_evidence_index

RECORDING = (
    Path(__file__).parents[2] / "evals/recordings/live-2026-10-29/scenario-01-blackout-sale.json"
)


def test_rendered_prompt_names_every_tool_call_and_its_tool() -> None:
    recorded = json.loads(RECORDING.read_text())
    records = extract_tool_call_records(messages_from_dict(recorded["messages"]))
    assert len(records) >= 6

    chain = build_claim_extractor_chain(
        ChatOpenAI(model="gpt-4o-mini", api_key=SecretStr("not-used"))
    )
    prompt = chain.first  # type: ignore[attr-defined]
    rendered = prompt.invoke(
        {"finding_text": "x", "evidence_index": format_evidence_index(records)}
    ).to_string()

    for r in records:
        assert f"{r.tool_call_id}: {r.tool_name}(" in rendered
    assert "in_blackout" in rendered
