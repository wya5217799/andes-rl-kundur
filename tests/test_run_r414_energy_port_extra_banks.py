"""Directed tests for the R414 energy-port extra-banks runner and banks.

Windows-safe: frozen bank validity, contract shape, per-block decision math
(with a stubbed phase summarizer), and serial capacity payload fields.
The WSL-only lifecycle runs through the scratch launcher in the sealed
round itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

import run_r414_energy_port_extra_banks as runner  # noqa: E402
from andes_rl_kundur.evaluation import soft_spot_energy_port_banks as banks  # noqa: E402


def test_banks_frozen_and_valid() -> None:
    assert len(banks.BLOCKS) == 3
    assert banks.block_ids() == [
        "a4_conditions_b",
        "a4_md_relaxed",
        "a4_md_stiff",
    ]
    for block in banks.BLOCKS:
        assert block["probe_condition"]["delta_u"]
        assert len(block["disturbance_conditions"]) == 2
        assert all(condition["delta_u"] for condition in block["disturbance_conditions"])
        assert block["vsg_m0"] > 0.0
        assert len(block["d0_per_agent"]) == 4
        assert all(value > 0.0 for value in block["d0_per_agent"])
    assert banks.block_by_id("a4_md_relaxed")["vsg_m0"] == 170.0
    with pytest.raises(ValueError):
        banks.block_by_id("missing")


def test_blocks_canonical_json_round_trip() -> None:
    """R414-abort lesson: the seal content and the load-time comparison must
    share one JSON-canonical form (tuples become lists)."""
    import json as _json

    canonical = runner._blocks_canonical()
    assert canonical == _json.loads(
        _json.dumps([dict(block) for block in banks.BLOCKS])
    )
    # the raw in-memory form differs (tuples), which is exactly the drift
    # that aborted R414 before the fix
    assert canonical != [dict(block) for block in banks.BLOCKS]
    assert canonical[1]["d0_per_agent"] == [115.0, 115.0, 115.0, 115.0]


def test_build_block_contract_shape() -> None:
    block = banks.block_by_id("a4_md_stiff")
    contract = runner.build_block_contract(block)
    assert contract["round"] == "R414"
    assert contract["development"]["arm_ids"] == list(banks.EVAL_ARMS)
    assert contract["development"]["record_count"] == 30
    assert contract["development"]["probe_condition"]["delta_u"] == {"PQ_0": -0.45}
    assert contract["r414"]["block_id"] == "a4_md_stiff"
    assert contract["r414"]["vsg_m0"] == 230.0
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
        banks.CANDIDATE_ARM: {
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
    assert abs(summary["probe_cross_ratio"] - 1.05) < 1e-12
    assert summary["strict_cross_pass"] is False


def test_block_summary_fail_on_r_d(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        runner,
        "summarize_phase_records",
        lambda records, phase, contract: {
            "arm_summaries": _synthetic_summaries(
                local_diff=10.0,
                local_off=4.0,
                candidate_diff=9.6,  # r_d 0.96 > 0.95
                candidate_off=3.0,
                zero_diff=11.0,
            )
        },
    )
    block = banks.block_by_id("a4_conditions_b")
    summary = runner._block_summary([], runner.build_block_contract(block))
    assert summary["passed"] is False
    assert summary["differential_ratio"] > 0.95


def test_block_summary_fail_on_guards(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        runner,
        "summarize_phase_records",
        lambda records, phase, contract: {
            "arm_summaries": _synthetic_summaries(
                local_diff=10.0,
                local_off=4.0,
                candidate_diff=5.0,
                candidate_off=2.0,
                zero_diff=11.0,
                candidate_guards=False,
            )
        },
    )
    block = banks.block_by_id("a4_conditions_b")
    summary = runner._block_summary([], runner.build_block_contract(block))
    assert summary["passed"] is False
    assert summary["candidate_guards_pass"] is False
