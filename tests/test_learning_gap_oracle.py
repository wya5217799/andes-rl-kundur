import platform

import numpy as np
import pytest

import andes_rl_kundur.evaluation.learning_gap_analysis_repair as analysis_repair
from andes_rl_kundur.evaluation.learning_gap_oracle import (
    BASELINE_CONTROLLER,
    CANDIDATE_NAMES,
    CANDIDATE_PATTERNS,
    COMMON_GUARD_ENDPOINTS,
    ENDPOINTS,
    PRIMARY_ENDPOINTS,
    RESTORATION_GUARD_ENDPOINTS,
    FrozenZeroSumInertiaPulse,
    audit_zero_sum_action,
    classify_learning_gap,
    frozen_learning_gap_contract,
    run_learning_gap_scenario,
    select_outcome_oracle,
    summarise_learning_gap_trace,
)

IS_WSL = platform.system() == "Linux" and "microsoft" in platform.release().lower()


def test_frozen_hadamard_library_spans_full_zero_sum_subspace():
    contract = frozen_learning_gap_contract()
    unsigned = np.asarray(
        [
            CANDIDATE_PATTERNS["h1_pos"],
            CANDIDATE_PATTERNS["h2_pos"],
            CANDIDATE_PATTERNS["h3_pos"],
        ],
        dtype=float,
    )

    assert tuple(contract["schedule"]["candidate_order"]) == CANDIDATE_NAMES
    assert len(CANDIDATE_NAMES) == 6
    assert np.allclose(np.sum(unsigned, axis=1), 0.0)
    assert np.linalg.matrix_rank(unsigned) == 3
    assert np.allclose(unsigned @ unsigned.T, 4.0 * np.eye(3))
    for name in ("h1", "h2", "h3"):
        assert np.array_equal(
            -np.asarray(CANDIDATE_PATTERNS[f"{name}_pos"]),
            np.asarray(CANDIDATE_PATTERNS[f"{name}_neg"]),
        )


@pytest.mark.parametrize("candidate_name", CANDIDATE_NAMES)
def test_zero_sum_pulse_preserves_fleet_mean_inertia(candidate_name):
    controller = FrozenZeroSumInertiaPulse(candidate_name)
    obs = {index: np.zeros(1, dtype=np.float32) for index in range(4)}

    active = np.asarray(
        [controller(0, obs, 4)[index] for index in range(4)],
        dtype=float,
    )
    inactive = np.asarray(
        [controller(15, obs, 4)[index] for index in range(4)],
        dtype=float,
    )

    assert sorted(active[:, 0]) == pytest.approx([0.0, 0.0, 0.5, 0.5])
    assert np.mean(active[:, 0]) == pytest.approx(0.25)
    assert np.sum(active[:, 0] - 0.25) == pytest.approx(0.0)
    assert np.all(active[:, 1] == 0.0)
    assert np.all(inactive == 0.0)
    assert np.mean(200.0 + 600.0 * active[:, 0]) == pytest.approx(350.0)


def _summary(
    *,
    sync=10.0,
    interarea=10.0,
    rocof=10.0,
    peak=10.0,
    iae=10.0,
    final=10.0,
):
    return {
        "normalized_sync_loss_hz2": sync,
        "fast_inter_area_iae_hz_s": interarea,
        "max_abs_rocof_hz_s": rocof,
        "worst_bus_peak_abs_hz": peak,
        "vsg_mean_iae_hz_s": iae,
        "final_window_common_abs_mean_hz": final,
        "bess_constraint_violation_count": 0,
        "bess_saturation_reason_count": 0,
    }


def test_learning_gap_summary_counts_storage_saturation_reasons(monkeypatch):
    monkeypatch.setattr(
        analysis_repair,
        "_sealed_summarise_learning_gap_trace",
        lambda record, **kwargs: {"bess_constraint_violation_count": 0},
    )
    record = {
        "traces": [
            {"bess_saturation_reasons": ["", "soc_max", None, ""]},
            {"bess_saturation_reasons": [[], [], [], []]},
        ]
    }

    summary = (
        analysis_repair.summarise_learning_gap_trace_with_saturation_count(
            record
        )
    )

    assert summary["bess_saturation_reason_count"] == 1


def test_outcome_oracle_selects_best_jointly_improving_candidate_and_falls_back():
    baselines = {
        "s0": _summary(),
        "s1": _summary(),
    }
    candidate_grid = {
        scenario: {name: _summary() for name in CANDIDATE_NAMES}
        for scenario in baselines
    }
    candidate_grid["s0"]["h1_pos"] = _summary(sync=8.0, interarea=9.0)
    candidate_grid["s0"]["h2_pos"] = _summary(sync=7.0, interarea=9.5)
    candidate_grid["s0"]["h3_pos"] = _summary(sync=6.0, interarea=9.0, rocof=11.0)
    candidate_grid["s1"]["h1_pos"] = _summary(sync=8.0, interarea=10.1)
    validity = {
        scenario: {name: True for name in CANDIDATE_NAMES}
        for scenario in baselines
    }

    selection, selected = select_outcome_oracle(
        baselines,
        candidate_grid,
        valid_candidates=validity,
    )

    assert selection["scenarios"]["s0"]["selected"] == "h2_pos"
    assert selection["scenarios"]["s1"]["selected"] == BASELINE_CONTROLLER
    assert selection["nonbaseline_selection_count"] == 1
    assert selected["s0"]["normalized_sync_loss_hz2"] == pytest.approx(7.0)
    h3_row = next(
        row
        for row in selection["scenarios"]["s0"]["candidate_rows"]
        if row["candidate"] == "h3_pos"
    )
    assert "max_abs_rocof_hz_s_over_5pct" in h3_row["reasons"]


def _contrast(*, primary_clear=(), guard_ok=True):
    endpoints = {}
    for endpoint in ENDPOINTS:
        if endpoint in primary_clear:
            point, upper = -3.0, -0.2
        elif endpoint in (*COMMON_GUARD_ENDPOINTS, *RESTORATION_GUARD_ENDPOINTS):
            point, upper = ((1.0, 4.0) if guard_ok else (3.0, 6.0))
        else:
            point, upper = -1.0, 0.5
        endpoints[endpoint] = {
            "ratio_of_means_percent": {
                "point": point,
                "percentile_95_interval": [-4.0, upper],
            }
        }
    return {"endpoints": endpoints}


def _classify(primary_clear, **overrides):
    kwargs = {
        "contrast": _contrast(primary_clear=primary_clear),
        "nonbaseline_selection_count": 12,
        "provenance_guard_pass": True,
        "completion_guard_pass": True,
        "action_contract_guard_pass": True,
        "storage_contract_guard_pass": True,
        "storage_relative_guard_pass": True,
        "tail_guard_pass": True,
    }
    kwargs.update(overrides)
    return classify_learning_gap(**kwargs)


def test_learning_gap_gate_requires_both_differential_endpoints():
    result = _classify(PRIMARY_ENDPOINTS)
    assert result["classification"] == "LEARNING-GAP-PRESENT"


def test_learning_gap_gate_reports_partial_and_no_rl_needed():
    partial = _classify((PRIMARY_ENDPOINTS[0],))
    negative = _classify(())

    assert partial["classification"] == "LEARNING-GAP-PARTIAL"
    assert negative["classification"] == "NO-RL-NEEDED"


def test_learning_gap_gate_rejects_guarded_harm_and_invalid_contract():
    harm = _classify(
        PRIMARY_ENDPOINTS,
        contrast=_contrast(primary_clear=PRIMARY_ENDPOINTS, guard_ok=False),
    )
    invalid = _classify(PRIMARY_ENDPOINTS, action_contract_guard_pass=False)

    assert harm["classification"] == "NO-RL-NEEDED"
    assert invalid["classification"] == "INVALID"


@pytest.mark.skipif(not IS_WSL, reason="real ANDES integration runs only in WSL")
def test_learning_gap_runner_produces_exact_complete_smoke_trace():
    record = run_learning_gap_scenario(
        "r277_learning_gap_smoke",
        {"PQ_Bus14": 1.0},
        candidate_name="h1_pos",
        seed=42,
        steps=20,
    )

    assert record["completed"] is True
    assert record["tds_failed"] is False
    assert record["n_steps"] == 20
    assert record["traces"][0]["M_es"] == pytest.approx([500.0, 500.0, 200.0, 200.0])
    assert record["traces"][15]["M_es"] == pytest.approx([200.0] * 4)
    assert all(audit_zero_sum_action(record).values())
    summary = summarise_learning_gap_trace(
        record,
        final_window_steps=5,
        fast_window_steps=15,
    )
    assert summary["bess_constraint_violation_count"] == 0
