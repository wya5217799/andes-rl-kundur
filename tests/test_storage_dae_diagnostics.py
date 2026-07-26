from andes_rl_kundur.evaluation.feasibility_screen import (
    advance_common_completion_bracket,
    build_feasibility_screen_contract,
)
from andes_rl_kundur.evaluation.storage_dae_feasibility import (
    classify_storage_dae_attribution,
)


def _record(scenario, plant, *, completed):
    return {
        "scenario": scenario,
        "plant": plant,
        "completed": completed,
        "tds_failed": not completed,
        "provenance_valid": True,
    }


def _matching_envelope_records(failures, controls):
    records = []
    for scenario in failures:
        records.extend(
            [
                _record(scenario, "original_v4", completed=False),
                _record(scenario, "storage_zero", completed=False),
            ]
        )
    for scenario in controls:
        records.extend(
            [
                _record(scenario, "original_v4", completed=True),
                _record(scenario, "storage_zero", completed=True),
            ]
        )
    return records


def test_attribution_classifies_matching_failures_as_envelope_infeasible():
    failures = ["random_00", "random_05", "random_10"]
    controls = ["random_01", "random_11", "random_16", "random_09"]
    records = _matching_envelope_records(failures, controls)

    decision = classify_storage_dae_attribution(
        records,
        failure_scenarios=failures,
        control_scenarios=controls,
    )

    assert decision["classification"] == "ENVELOPE-INFEASIBLE"
    assert decision["completion_vectors_match"] is True
    assert decision["all_registered_failures_reproduced"] is True
    assert decision["all_controls_complete"] is True


def test_attribution_rejects_duplicate_rows_instead_of_overwriting_them():
    failures = ["random_00"]
    controls = ["random_01"]
    records = _matching_envelope_records(failures, controls)
    records.append(dict(records[0]))

    decision = classify_storage_dae_attribution(
        records,
        failure_scenarios=failures,
        control_scenarios=controls,
    )

    assert decision["classification"] == "UNRESOLVED/INVALID"


def test_attribution_classifies_storage_specific_failures_as_dae_confound():
    failures = ["random_00", "random_05"]
    controls = ["random_01"]
    records = []
    for scenario in failures:
        records.extend(
            [
                _record(scenario, "original_v4", completed=True),
                _record(scenario, "storage_zero", completed=False),
            ]
        )
    records.extend(
        [
            _record("random_01", "original_v4", completed=True),
            _record("random_01", "storage_zero", completed=True),
        ]
    )

    decision = classify_storage_dae_attribution(
        records,
        failure_scenarios=failures,
        control_scenarios=controls,
    )

    assert decision["classification"] == "STORAGE-DAE-CONFOUND"


def test_attribution_classifies_shared_and_storage_specific_failures_as_mixed():
    records = [
        _record("random_00", "original_v4", completed=False),
        _record("random_00", "storage_zero", completed=False),
        _record("random_05", "original_v4", completed=True),
        _record("random_05", "storage_zero", completed=False),
        _record("random_01", "original_v4", completed=True),
        _record("random_01", "storage_zero", completed=True),
    ]

    decision = classify_storage_dae_attribution(
        records,
        failure_scenarios=["random_00", "random_05"],
        control_scenarios=["random_01"],
    )

    assert decision["classification"] == "MIXED"


def test_common_completion_bisection_advances_only_when_plants_agree():
    complete = advance_common_completion_bracket(
        lower_complete=0.4419,
        upper_failed=2.1841,
        tested_magnitude=1.313,
        completion_by_plant={
            "original_v4": True,
            "storage_zero": True,
        },
    )
    failed = advance_common_completion_bracket(
        lower_complete=complete["lower_complete"],
        upper_failed=complete["upper_failed"],
        tested_magnitude=1.74855,
        completion_by_plant={
            "original_v4": False,
            "storage_zero": False,
        },
    )

    assert complete == {
        "lower_complete": 1.313,
        "upper_failed": 2.1841,
        "classification": "COMMON-COMPLETE",
    }
    assert failed == {
        "lower_complete": 1.313,
        "upper_failed": 1.74855,
        "classification": "COMMON-FAILED",
    }


def test_common_completion_bisection_stops_on_plant_mismatch():
    decision = advance_common_completion_bracket(
        lower_complete=0.4419,
        upper_failed=2.1841,
        tested_magnitude=1.313,
        completion_by_plant={
            "original_v4": True,
            "storage_zero": False,
        },
    )

    assert decision["classification"] == "PLANT-MISMATCH"
    assert decision["lower_complete"] == 0.4419
    assert decision["upper_failed"] == 2.1841


def test_feasibility_screen_retains_failures_and_reports_strata():
    records = [
        {
            "scenario": "positive_complete",
            "plant": "original_v4",
            "delta_u": {"PQ_Bus14": 0.5},
            "completed": True,
            "trace_sha256": "a" * 64,
        },
        {
            "scenario": "positive_complete",
            "plant": "storage_zero",
            "delta_u": {"PQ_Bus14": 0.5},
            "completed": True,
            "trace_sha256": "b" * 64,
        },
        {
            "scenario": "negative_failed",
            "plant": "original_v4",
            "delta_u": {"PQ_Bus15": -2.0},
            "completed": False,
            "trace_sha256": "c" * 64,
        },
        {
            "scenario": "negative_failed",
            "plant": "storage_zero",
            "delta_u": {"PQ_Bus15": -2.0},
            "completed": False,
            "trace_sha256": "d" * 64,
        },
    ]

    contract = build_feasibility_screen_contract(
        records,
        expected_plants=("original_v4", "storage_zero"),
        generated_bank_sha256="e" * 64,
        completion_evidence_sha256="f" * 64,
        controller_trace_count=0,
    )

    assert contract["scenario_count"] == 2
    assert contract["excluded_scenario_count"] == 1
    assert contract["excluded_fraction"] == 0.5
    assert contract["frozen_before_controller_evaluation"] is True
    assert contract["strata"]["PQ_Bus14|positive"] == {
        "scenario_count": 1,
        "excluded_scenario_count": 0,
    }
    assert contract["strata"]["PQ_Bus15|negative"] == {
        "scenario_count": 1,
        "excluded_scenario_count": 1,
    }
    assert [row["scenario"] for row in contract["retained_exclusions"]] == [
        "negative_failed"
    ]
    assert contract["decisions"][1]["disposition"] == "excluded-retained"


def test_feasibility_screen_cannot_be_frozen_after_controller_traces():
    records = [
        {
            "scenario": "case",
            "plant": "original_v4",
            "delta_u": {"PQ_Bus14": 0.5},
            "completed": True,
            "trace_sha256": "a" * 64,
        }
    ]

    try:
        build_feasibility_screen_contract(
            records,
            expected_plants=("original_v4",),
            generated_bank_sha256="e" * 64,
            completion_evidence_sha256="f" * 64,
            controller_trace_count=1,
        )
    except ValueError as exc:
        assert "before controller evaluation" in str(exc)
    else:
        raise AssertionError("post-controller feasibility seal was accepted")
