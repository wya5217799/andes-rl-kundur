from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_r300_relative_rocof_formal.py"
SPEC = importlib.util.spec_from_file_location("r300_formal", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
r300 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r300)


def test_formal_matrix_is_exactly_the_r299_predeclared_bank() -> None:
    assert len(r300.scenario_bank()) == 12
    assert len(r300.arm_bank()) == 3
    assert len(r300.job_bank()) == 36
    assert {row["tie_k"] for row in r300.scenario_bank()} == {1.375, 1.625}
    assert [arm["name"] for arm in r300.arm_bank()] == [
        "distributed_edge__kv",
        "distributed_edge__2kv",
        "central_vector__ks1",
    ]


def test_selection_contract_binds_classical_retune_and_gain() -> None:
    contract = r300._selection_contract()
    assert contract["selected_base_gain_system_pu_s_per_hz"] == r300.BASE_GAIN
    assert contract["selected_total_gain_system_pu_s_per_hz"] == 2.0 * r300.BASE_GAIN


def test_primary_gate_keeps_fast_materiality_and_sync_no_harm_separate() -> None:
    endpoints = {
        name: {
            "point": 0.98,
            "percentile_95_interval": [0.97, 0.99],
            "worst_individual_ratio": 1.0,
        }
        for name in (*r300.COMMON_ENDPOINTS, *r300.DIFFERENTIAL_ENDPOINTS)
    }
    assert r300._primary_gate({"candidate_over_reference": endpoints})["passed"] is True
    endpoints["normalized_sync_loss_hz2"] = {
        "point": 1.001,
        "percentile_95_interval": [0.99, 1.009],
        "worst_individual_ratio": 1.02,
    }
    gate = r300._primary_gate({"candidate_over_reference": endpoints})
    assert gate["component_pass"]["fast"] is True
    assert gate["component_pass"]["sync"] is False
    assert gate["passed"] is False
