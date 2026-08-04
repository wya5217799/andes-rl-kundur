from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_r295_consensus_timescale_probe.py"
SPEC = importlib.util.spec_from_file_location("r295_probe", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
r295 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r295)


def test_bank_changes_only_consensus_gain() -> None:
    assert [arm["consensus_gain"] for arm in r295.arm_bank()] == [1.0, 2.0, 4.0]
    assert len(r295.scenario_bank()) == 4
    assert len(r295.job_bank()) == 12
    fixed = [
        {key: value for key, value in arm.items() if key not in {"name", "consensus_gain"}}
        for arm in r295.arm_bank()
    ]
    assert fixed[0] == fixed[1] == fixed[2]


def test_graph_candidates_remain_inside_discrete_scalar_boundary() -> None:
    contract = r295._graph_spectral_contract()
    assert contract["eigenvalues"] == pytest.approx([0.0, 1.0, 1.0, 2.0], abs=1e-12)
    for factors in contract["candidate_discrete_factors_by_gain"].values():
        assert max(abs(value) for value in factors) <= 1.0 + 1e-12


def _rows(*, fast: float, sync: float, common: float = 1.0):
    return {
        name: {
            "vsg_mean_iae_hz_s": common,
            "worst_bus_peak_abs_hz": common,
            "max_abs_rocof_hz_s": common,
            "normalized_sync_loss_hz2": sync,
            "fast_inter_area_iae_hz_s": fast,
        }
        for name in ("a", "b", "c", "d")
    }


def test_joint_gate_requires_fast_gain_and_sync_no_harm() -> None:
    baseline = _rows(fast=1.0, sync=1.0)
    passing = r295.evaluate_candidate(_rows(fast=0.98, sync=1.005), baseline)
    failed_sync = r295.evaluate_candidate(_rows(fast=0.98, sync=1.02), baseline)
    failed_fast = r295.evaluate_candidate(_rows(fast=0.995, sync=0.98), baseline)
    assert passing["passed"] is True
    assert failed_sync["passed"] is False
    assert failed_fast["passed"] is False


def test_seal_declares_development_claim_boundary() -> None:
    payload = r295._seal_payload()
    assert payload["development_only"] is True
    assert payload["shard_count"] == 3
    assert "no held-out efficacy" in payload["claim_boundary"]
