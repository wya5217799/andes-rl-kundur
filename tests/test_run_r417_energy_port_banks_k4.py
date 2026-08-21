"""Directed tests for the R417 K=4.0 breadth runner and the shared banks.

Windows-safe: candidate/arm overrides, contract shape, per-block decision
math (stubbed summarizer).  The WSL-only lifecycle runs through the
scratch launcher in the sealed round itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

import run_r417_energy_port_banks_k4 as runner  # noqa: E402
from andes_rl_kundur.evaluation import soft_spot_energy_port_banks as banks  # noqa: E402


def test_candidate_and_arms_override() -> None:
    assert runner.CANDIDATE_ARM == "bandpass_k4"
    assert runner.EVAL_ARMS == (
        "zero_feedback",
        "local_feasibility_native",
        "bandpass_k4",
    )


def test_contract_shape() -> None:
    block = banks.block_by_id("a4_conditions_b")
    contract = runner.build_block_contract(block)
    assert contract["round"] == "R417"
    assert contract["development"]["arm_ids"] == list(runner.EVAL_ARMS)
    assert contract["development"]["record_count"] == 30
    assert contract["training_authorized"] is False


def _synthetic_summaries(
    *,
    local_diff: float,
    local_off: float,
    candidate_diff: float,
    candidate_off: float,
    zero_diff: float,
    candidate_guards: bool = True,
    reference_guards: bool = True,
) -> dict:
    return {
        banks.LOCAL_ARM: {
            "disturbance": {"mean_differential_frequency_energy_hz2_s": local_diff},
            "probe": {"off_diagonal_response_energy_hz2_s": local_off},
            "guards_pass": reference_guards,
            "guard_errors": [],
        },
        banks.ZERO_ARM: {
            "disturbance": {"mean_differential_frequency_energy_hz2_s": zero_diff},
            "probe": {"off_diagonal_response_energy_hz2_s": local_off},
            "guards_pass": reference_guards,
            "guard_errors": [],
        },
        "bandpass_k4": {
            "disturbance": {"mean_differential_frequency_energy_hz2_s": candidate_diff},
            "probe": {"off_diagonal_response_energy_hz2_s": candidate_off},
            "guards_pass": candidate_guards,
            "guard_errors": ["probe rank collapse"] if not candidate_guards else [],
        },
    }


def test_block_summary_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        runner,
        "summarize_phase_records",
        lambda records, phase, contract: {
            "arm_summaries": _synthetic_summaries(
                local_diff=10.0,
                local_off=4.0,
                candidate_diff=9.0,
                candidate_off=4.2,
                zero_diff=11.0,
            )
        },
    )
    block = banks.block_by_id("a4_conditions_b")
    summary = runner._block_summary([], runner.build_block_contract(block))
    assert summary["passed"] is True
    assert abs(summary["differential_ratio"] - 0.9) < 1e-12


def test_block_summary_fail_on_r_d(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        runner,
        "summarize_phase_records",
        lambda records, phase, contract: {
            "arm_summaries": _synthetic_summaries(
                local_diff=10.0,
                local_off=4.0,
                candidate_diff=9.6,
                candidate_off=3.0,
                zero_diff=11.0,
            )
        },
    )
    block = banks.block_by_id("a4_conditions_b")
    summary = runner._block_summary([], runner.build_block_contract(block))
    assert summary["passed"] is False
    assert summary["differential_ratio"] > 0.95
