from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_r296_relative_rocof_probe.py"
SPEC = importlib.util.spec_from_file_location("r296_probe", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
r296 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r296)


def test_gain_derivation_and_job_bank_are_frozen() -> None:
    assert r296.FILTER_MAGNITUDE_PER_S == pytest.approx(4.094321498573086)
    assert r296.RESIDUAL_GAINS == pytest.approx(
        [0.0, 0.06106017812405001, 0.12212035624810003]
    )
    assert len(r296.scenario_bank()) == 4
    assert len(r296.arm_bank()) == 3
    assert len(r296.job_bank()) == 12


def test_arms_change_only_residual_treatment() -> None:
    fixed = [
        {
            key: value
            for key, value in arm.items()
            if key not in {"name", "relative_rocof_gain", "target_static_sync_fraction"}
        }
        for arm in r296.arm_bank()
    ]
    assert fixed[0] == fixed[1] == fixed[2]


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


def test_joint_gate_requires_endpoint_gain_and_nonzero_residual() -> None:
    baseline = _rows(fast=1.0, sync=1.0)
    passing = r296.evaluate_candidate(
        _rows(fast=0.98, sync=1.005), baseline, residual_rms=1e-3
    )
    zero = r296.evaluate_candidate(
        _rows(fast=0.98, sync=1.005), baseline, residual_rms=0.0
    )
    weak = r296.evaluate_candidate(
        _rows(fast=0.995, sync=0.98), baseline, residual_rms=1e-3
    )
    assert passing["passed"] is True
    assert zero["passed"] is False
    assert weak["passed"] is False


def test_seal_keeps_development_and_claim_boundaries() -> None:
    payload = r296._seal_payload()
    assert payload["development_only"] is True
    assert payload["shard_count"] == 3
    assert "no held-out efficacy" in payload["claim_boundary"]
    assert payload["zero_sum_reason"].startswith("undirected regular ring")
