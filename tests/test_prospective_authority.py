from collections import Counter

from andes_rl_kundur.evaluation.prospective_authority import (
    assess_screened_authority_bank,
    audit_zero_support_screen_record,
    build_stratified_authority_candidates,
)


def test_candidate_bank_is_balanced_signed_multilocation_and_nontrivial():
    bank = build_stratified_authority_candidates(
        seed=2026072603,
        repository_head="test-head",
        generator_source_sha256="a" * 64,
    )

    assert bank["scenario_count"] == 24
    assert bank["generator_arguments"] == {
        "n": 24,
        "seed": 2026072603,
        "include_anchors": False,
    }
    assert bank["repository_head"] == "test-head"
    assert bank["generator_source_sha256"] == "a" * 64

    scenarios = bank["scenarios"]
    assert len({row["name"] for row in scenarios}) == 24
    assert Counter(
        (row["location"], row["sign"]) for row in scenarios
    ) == {
        ("PQ_0", "positive"): 3,
        ("PQ_0", "negative"): 3,
        ("PQ_1", "positive"): 3,
        ("PQ_1", "negative"): 3,
        ("PQ_Bus14", "positive"): 3,
        ("PQ_Bus14", "negative"): 3,
        ("PQ_Bus15", "positive"): 3,
        ("PQ_Bus15", "negative"): 3,
    }
    assert Counter(row["severity"] for row in scenarios) == {
        "moderate": 8,
        "strong": 8,
        "edge": 8,
    }

    bounds = {
        "moderate": (0.65, 0.85),
        "strong": (0.95, 1.15),
        "edge": (1.35, 1.50),
    }
    magnitudes = []
    for row in scenarios:
        location, signed_magnitude = next(iter(row["delta_u"].items()))
        magnitude = abs(signed_magnitude)
        lower, upper = bounds[row["severity"]]
        assert location == row["location"]
        assert lower <= magnitude <= upper
        assert (signed_magnitude > 0) == (row["sign"] == "positive")
        magnitudes.append(magnitude)
    assert sum(magnitudes) / len(magnitudes) >= 0.95
    assert max(magnitudes) >= 1.35

    assert bank == build_stratified_authority_candidates(
        seed=2026072603,
        repository_head="test-head",
        generator_source_sha256="a" * 64,
    )
    assert bank["scenarios"] != build_stratified_authority_candidates(
        seed=2026072604,
        repository_head="test-head",
        generator_source_sha256="a" * 64,
    )["scenarios"]


def test_screen_assessment_passes_all_complete_balanced_candidates():
    bank = build_stratified_authority_candidates(
        seed=2026072603,
        repository_head="test-head",
        generator_source_sha256="a" * 64,
    )
    records = [
        {
            "scenario": scenario["name"],
            "plant": "storage_zero",
            "delta_u": scenario["delta_u"],
            "completed": True,
            "tds_failed": False,
            "n_steps": 300,
            "requested_steps": 300,
            "physical_valid": True,
            "trace_sha256": f"{index + 1:064x}",
        }
        for index, scenario in enumerate(bank["scenarios"])
    ]

    assessment = assess_screened_authority_bank(
        bank,
        records,
        generated_bank_sha256="b" * 64,
        completion_evidence_sha256="c" * 64,
        controller_trace_count=0,
    )

    assert assessment["decision"]["classification"] == "PASS"
    assert all(assessment["decision"]["guards"].values())
    assert assessment["feasibility_contract"]["scenario_count"] == 24
    assert assessment["feasibility_contract"]["excluded_scenario_count"] == 0
    assert assessment["feasibility_contract"]["retained_exclusions"] == []
    assert assessment["formal_bank"]["scenario_count"] == 24
    assert assessment["formal_bank"]["scenarios"] == bank["scenarios"]
    assert assessment["included_nontriviality"]["edge_count"] == 8
    assert assessment["included_nontriviality"]["location_sign_counts"] == {
        "PQ_0|negative": 3,
        "PQ_0|positive": 3,
        "PQ_1|negative": 3,
        "PQ_1|positive": 3,
        "PQ_Bus14|negative": 3,
        "PQ_Bus14|positive": 3,
        "PQ_Bus15|negative": 3,
        "PQ_Bus15|positive": 3,
    }


def test_zero_support_audit_proves_power_soc_and_md_are_frozen():
    record = {
        "scenario": "case",
        "controller": "zero_support",
        "delta_u": {"PQ_0": 1.0},
        "requested_steps": 2,
        "n_steps": 2,
        "completed": True,
        "tds_failed": False,
        "traces": [
            {
                "M_es": [200.0] * 4,
                "D_es": [100.0] * 4,
                "bess_requested_power_system_pu": [0.0] * 4,
                "bess_commanded_power_system_pu": [0.0] * 4,
                "bess_actual_power_system_pu": [0.0] * 4,
                "bess_soc": [0.5] * 4,
                "bess_constraint_violations": [],
            },
            {
                "M_es": [200.0] * 4,
                "D_es": [100.0] * 4,
                "bess_requested_power_system_pu": [0.0] * 4,
                "bess_commanded_power_system_pu": [0.0] * 4,
                "bess_actual_power_system_pu": [0.0] * 4,
                "bess_soc": [0.5] * 4,
                "bess_constraint_violations": [],
            },
        ],
    }

    audit = audit_zero_support_screen_record(
        record,
        trace_sha256="d" * 64,
    )

    assert audit["physical_valid"] is True
    assert audit["max_abs_requested_power"] == 0.0
    assert audit["max_abs_commanded_power"] == 0.0
    assert audit["max_abs_actual_power"] == 0.0
    assert audit["min_soc"] == 0.5
    assert audit["max_soc"] == 0.5
    assert audit["m_unique"] == [200.0]
    assert audit["d_unique"] == [100.0]
    assert audit["constraint_violation_count"] == 0
    assert audit["trace_sha256"] == "d" * 64


def test_screen_assessment_rejects_non_storage_baseline_evidence():
    bank = build_stratified_authority_candidates(
        seed=2026072603,
        repository_head="test-head",
        generator_source_sha256="a" * 64,
    )
    records = [
        {
            "scenario": scenario["name"],
            "plant": "storage_zero",
            "delta_u": scenario["delta_u"],
            "completed": True,
            "tds_failed": False,
            "n_steps": 300,
            "requested_steps": 300,
            "physical_valid": True,
            "trace_sha256": f"{index + 1:064x}",
        }
        for index, scenario in enumerate(bank["scenarios"])
    ]
    records[0]["plant"] = "original_v4"

    try:
        assess_screened_authority_bank(
            bank,
            records,
            generated_bank_sha256="b" * 64,
            completion_evidence_sha256="c" * 64,
            controller_trace_count=0,
        )
    except ValueError as exc:
        assert "storage_zero" in str(exc)
    else:
        raise AssertionError("non-storage screen evidence was accepted")


def test_screen_retains_four_exclusions_but_fifth_makes_bank_invalid():
    bank = build_stratified_authority_candidates(
        seed=2026072603,
        repository_head="test-head",
        generator_source_sha256="a" * 64,
    )
    records = [
        {
            "scenario": scenario["name"],
            "plant": "storage_zero",
            "delta_u": scenario["delta_u"],
            "completed": True,
            "tds_failed": False,
            "n_steps": 300,
            "requested_steps": 300,
            "physical_valid": True,
            "trace_sha256": f"{index + 1:064x}",
        }
        for index, scenario in enumerate(bank["scenarios"])
    ]
    moderate_by_stratum = {}
    for scenario in bank["scenarios"]:
        if scenario["severity"] == "moderate":
            moderate_by_stratum[
                (scenario["location"], scenario["sign"])
            ] = scenario["name"]
    first_five = list(moderate_by_stratum.values())[:5]
    by_name = {row["scenario"]: row for row in records}
    for name in first_five[:4]:
        by_name[name]["physical_valid"] = False

    four_excluded = assess_screened_authority_bank(
        bank,
        records,
        generated_bank_sha256="b" * 64,
        completion_evidence_sha256="c" * 64,
        controller_trace_count=0,
    )

    assert four_excluded["decision"]["classification"] == "PASS"
    assert four_excluded["formal_bank"]["scenario_count"] == 20
    assert (
        four_excluded["feasibility_contract"]["excluded_scenario_count"]
        == 4
    )
    assert {
        row["scenario"]
        for row in four_excluded["feasibility_contract"][
            "retained_exclusions"
        ]
    } == set(first_five[:4])

    by_name[first_five[4]]["physical_valid"] = False
    five_excluded = assess_screened_authority_bank(
        bank,
        records,
        generated_bank_sha256="b" * 64,
        completion_evidence_sha256="d" * 64,
        controller_trace_count=0,
    )

    assert five_excluded["decision"]["classification"] == "INVALID"
    assert five_excluded["decision"]["guards"]["included_count_ge_20"] is False
    assert five_excluded["decision"]["guards"]["excluded_count_le_4"] is False
    assert five_excluded["formal_bank"]["scenario_count"] == 19
