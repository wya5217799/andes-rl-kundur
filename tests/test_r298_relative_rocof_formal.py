from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_r298_relative_rocof_formal.py"
SPEC = importlib.util.spec_from_file_location("r298_formal", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
r298 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r298)


def test_formal_bank_and_arm_matrix_are_exact() -> None:
    assert len(r298.scenario_bank()) == 12
    assert len(r298.arm_bank()) == 3
    assert len(r298.job_bank()) == 36
    assert {row["tie_k"] for row in r298.scenario_bank()} == {1.25, 1.75}
    assert [arm["name"] for arm in r298.arm_bank()] == [
        "distributed_dapi_local__kv0",
        "distributed_dapi_local__kv100pct",
        "central_vector__ks1",
    ]


def test_selection_contract_binds_r297_bank_and_gain() -> None:
    contract = r298._selection_contract()
    assert contract["selected_gain_system_pu_s_per_hz"] == r298.selection.FULL_GAIN
    assert len(r298._seal_payload()["scenarios"]) == 12


def test_primary_gate_separates_fast_materiality_from_sync_no_harm() -> None:
    endpoints = {}
    for name in (*r298.COMMON_ENDPOINTS, *r298.DIFFERENTIAL_ENDPOINTS):
        endpoints[name] = {
            "point": 0.98,
            "percentile_95_interval": [0.97, 0.99],
            "worst_individual_ratio": 1.0,
        }
    passing = r298._primary_gate({"candidate_over_reference": endpoints})
    assert passing["passed"] is True
    endpoints["normalized_sync_loss_hz2"] = {
        "point": 1.001,
        "percentile_95_interval": [0.99, 1.009],
        "worst_individual_ratio": 1.02,
    }
    tradeoff = r298._primary_gate({"candidate_over_reference": endpoints})
    assert tradeoff["component_pass"]["fast"] is True
    assert tradeoff["component_pass"]["sync"] is False
    assert tradeoff["passed"] is False
