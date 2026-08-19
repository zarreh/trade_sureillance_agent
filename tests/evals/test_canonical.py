from evals.canonical import run_canonical_eval


def test_all_ten_canonical_scenarios_match_expected_disposition() -> None:
    results, report = run_canonical_eval()
    mismatches = {
        r.scenario_id: (r.expected_disposition, r.actual_disposition)
        for r in results
        if r.actual_disposition != r.expected_disposition
    }
    assert not mismatches, mismatches
    assert report.n == 10
    assert report.disposition_accuracy == 1.0


def test_scenario_5_10b5_1_clears_despite_blackout_window() -> None:
    results, _ = run_canonical_eval()
    by_id = {r.scenario_id: r for r in results}
    assert by_id["scenario-05-10b5-1-sale"].actual_disposition == "clear"


def test_scenario_6_tax_withholding_clears_at_high_value() -> None:
    results, _ = run_canonical_eval()
    by_id = {r.scenario_id: r for r in results}
    assert by_id["scenario-06-tax-withholding"].actual_disposition == "clear"


def test_scenario_7_f_line_does_not_clear_the_unrelated_s_line() -> None:
    results, _ = run_canonical_eval()
    by_id = {r.scenario_id: r for r in results}
    assert by_id["scenario-07-f-does-not-clear-s"].actual_disposition == "escalate"


def test_scenario_9_amendment_clears_once_the_superseded_original_is_excluded() -> None:
    results, _ = run_canonical_eval()
    by_id = {r.scenario_id: r for r in results}
    assert by_id["scenario-09-amend-away"].actual_disposition == "clear"


def test_every_scenario_produces_a_correctly_ordered_plan() -> None:
    results, report = run_canonical_eval()
    assert all(r.plan_ok for r in results)
    assert report.tool_call_accuracy == 1.0


def test_every_claim_is_grounded_since_the_oracle_never_invents_facts() -> None:
    _, report = run_canonical_eval()
    assert report.unsupported_claim_rate == 0.0
    assert report.citation_coverage_pct == 100.0
