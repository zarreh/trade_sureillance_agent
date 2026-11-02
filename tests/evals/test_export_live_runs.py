import json

from evals.export_live_runs import OUTPUT_PATH, build_document


def test_runs_are_newest_first_and_match_the_committed_file() -> None:
    document = build_document()
    dates = [r["run_date"] for r in document["runs"]]
    assert dates == sorted(dates, reverse=True)
    assert all(r["n"] == len(r["scenarios"]) for r in document["runs"])
    assert json.loads(OUTPUT_PATH.read_text()) == document
