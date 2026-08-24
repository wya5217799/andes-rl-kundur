"""Directed tests for the R453 offline aggregation repair.

R478 (2026-08-24): the M/D base-convention correction changed the V4 env,
so the R452 seal no longer matches ``v4_environment``. The frozen R453
runner stays byte-identical and fails closed on that drift; the drift
contract is pinned here at the test layer instead of weakening the runner.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_r453_m5_aggregate_repair_test",
    ROOT / "scripts/run_r453_m5_aggregate_repair.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _summary(*, valid: bool, rms: float = 1.0, tv: float = 1.0) -> dict:
    return {
        "disturbance_differential_energy": 0.95,
        "off_diagonal_response_energy": 0.95,
        "common_frequency_iae_hz_s": 1.0,
        "worst_unit_peak_hz": 1.0,
        "worst_rocof_hz_s": 1.0,
        "action_rms": rms,
        "action_total_variation": tv,
        "action_saturation_fraction": 0.0,
        "valid": valid,
    }


def _static() -> dict:
    return {
        "disturbance_differential_energy": 1.0,
        "off_diagonal_response_energy": 1.0,
        "common_frequency_iae_hz_s": 1.0,
        "worst_unit_peak_hz": 1.0,
        "worst_rocof_hz_s": 1.0,
        "action_rms": 1.0,
        "action_total_variation": 1.0,
        "action_saturation_fraction": 0.0,
        "valid": True,
    }


def test_endpoint_only_is_distinct_from_valid_endpoint() -> None:
    guard = MODULE.candidate_guard(_summary(valid=False), _static())
    assert guard["joint_endpoint_eligible"] is True
    assert guard["valid_endpoint_eligible"] is False
    assert guard["joint_guard_feasible"] is False


def test_guard_boundaries_are_inclusive() -> None:
    summary = _summary(valid=True, rms=1.10, tv=1.10)
    summary["common_frequency_iae_hz_s"] = 1.03
    summary["worst_unit_peak_hz"] = 1.03
    summary["worst_rocof_hz_s"] = 1.03
    summary["action_saturation_fraction"] = 0.05
    guard = MODULE.candidate_guard(summary, _static())
    assert guard["joint_guard_feasible"] is True


def test_pareto_retains_tied_generated_ids() -> None:
    rows = [
        {"candidate_id": "a", "objectives": [1.0, 1.0, 1.0, 1.0]},
        {"candidate_id": "b", "objectives": [1.0, 1.0, 1.0, 1.0]},
        {"candidate_id": "c", "objectives": [2.0, 2.0, 2.0, 2.0]},
    ]
    assert [row["candidate_id"] for row in MODULE.nondominated(rows)] == ["a", "b"]


def test_r478_env_drift_is_the_only_declared_sealed_drift() -> None:
    """The frozen R453 runner must fail closed on the R478 v4-env change,
    and every OTHER sealed source must still match its R452 hash."""
    seal, _seal_sha = MODULE.read_verified_json(MODULE.PARENT_SEAL)
    assert seal["round"] == MODULE.PARENT_ROUND
    for name, entry in seal.get("sources", {}).items():
        path = ROOT / entry["path"]
        digest = MODULE.sha256_file(path)
        if name == "shard_driver":
            # Pre-existing R476 allowlist entry (drifted driver); still inside
            # the frozen runner's allowlist and not part of R478.
            continue
        if name == "v4_environment":
            assert digest != entry["sha256"], (
                "v4_environment no longer drifts; the R478 declaration "
                "must be re-checked"
            )
            continue
        assert digest == entry["sha256"], f"undeclared drift: {entry['path']}"
    with pytest.raises(
        RuntimeError,
        match=r"R452 sealed source drift: src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
    ):
        MODULE.verify_parent()


@pytest.mark.xfail(
    raises=RuntimeError,
    strict=True,
    reason=(
        "blocked by the R478 declared v4-env drift: the frozen R453 runner "
        "fails closed and its inventory cannot be built until a successor "
        "re-keys the R452 seal"
    ),
)
def test_r452_count_bug_is_exposed_without_changing_primary_ids() -> None:
    parent = MODULE.verify_parent()
    comparison = MODULE._compare_parent_profiles(parent["profiles"])
    assert comparison["eval_b"]["parent_stored_count"] == 25
    assert comparison["eval_b"]["repaired_endpoint_only_count"] == 47
    assert comparison["eval_b"]["explicit_valid_endpoint_count"] == 25
    assert comparison["eval_d"]["parent_stored_count"] == 13
    assert comparison["eval_d"]["repaired_endpoint_only_count"] == 16
    assert comparison["eval_d"]["explicit_valid_endpoint_count"] == 13
    assert all(
        row["joint_guard_feasible_ids_match"] and row["pareto_ids_match"]
        for row in comparison.values()
    )
