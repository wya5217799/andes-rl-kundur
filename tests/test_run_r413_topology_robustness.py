"""Directed tests for the R413 topology-robustness runner (A2 successor).

Windows-safe: contract shape, variant helpers, anchor math, rung selection,
per-variant endpoint decision (stubbed summarizer), and the graceful
EIG-gate failure path (stubbed env builder).  The WSL-only lifecycle runs
through the scratch launcher in the sealed round itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

import run_r413_topology_robustness as runner  # noqa: E402


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
        runner.LOCAL_ARM: {
            "disturbance": {"mean_differential_frequency_energy_hz2_s": local_diff},
            "probe": {"off_diagonal_response_energy_hz2_s": local_off},
            "guards_pass": reference_guards,
            "guard_errors": [],
        },
        runner.ZERO_ARM: {
            "disturbance": {"mean_differential_frequency_energy_hz2_s": zero_diff},
            "probe": {"off_diagonal_response_energy_hz2_s": local_off},
            "guards_pass": reference_guards,
            "guard_errors": [],
        },
        runner.CANDIDATE_ARM: {
            "disturbance": {"mean_differential_frequency_energy_hz2_s": candidate_diff},
            "probe": {"off_diagonal_response_energy_hz2_s": candidate_off},
            "guards_pass": candidate_guards,
            "guard_errors": ["probe rank collapse"] if not candidate_guards else [],
        },
    }


def test_variant_bank_frozen() -> None:
    ids = runner.variant_ids()
    assert len(ids) == 12
    assert len(set(ids)) == 12
    assert ids[0] == "nominal"
    assert {v["kind"] for v in runner.TOPOLOGY_VARIANTS} == {
        "none",
        "outage",
        "impedance",
    }
    with pytest.raises(ValueError):
        runner.variant_by_id("missing")


def test_build_variant_contract_shape() -> None:
    variant = {"variant_id": "out_test", "kind": "outage", "line_idx": "Line_1"}
    contract = runner.build_variant_contract(variant)
    assert contract["round"] == "R413"
    assert contract["development"]["arm_ids"] == list(runner.EVAL_ARMS)
    assert contract["development"]["record_count"] == 30
    assert contract["r412"]["variant_id"] == "out_test"
    assert contract["training_authorized"] is False


def test_variant_summary_pass_and_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    contract = runner.build_variant_contract(
        {"variant_id": "nominal", "kind": "none"}
    )
    summary = runner._variant_summary([], contract)
    assert summary["passed"] is True
    assert abs(summary["differential_ratio"] - 0.9) < 1e-12
    assert abs(summary["probe_cross_ratio"] - 1.05) < 1e-12
    assert summary["strict_cross_pass"] is False


def test_variant_summary_fail_on_guards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    contract = runner.build_variant_contract(
        {"variant_id": "nominal", "kind": "none"}
    )
    summary = runner._variant_summary([], contract)
    assert summary["passed"] is False
    assert summary["candidate_guards_pass"] is False


def test_anchor_verdict_reproduced() -> None:
    anchor = runner._anchor_verdict(
        runner.BASE_ANCHOR["r_d"] * (1.0 + 1e-9),
        runner.BASE_ANCHOR["r_cross"] * (1.0 - 1e-9),
    )
    assert anchor["verdict"] == "BASE-ANCHOR-REPRODUCED"


def test_anchor_verdict_drift() -> None:
    anchor = runner._anchor_verdict(
        runner.BASE_ANCHOR["r_d"] * 1.01,
        runner.BASE_ANCHOR["r_cross"],
    )
    assert anchor["verdict"] == "BASE-ANCHOR-DRIFT"


def test_rung_selection_marginal_and_memory() -> None:
    throughput = {1: 0.10, 2: 0.19, 4: 0.36, 8: 0.37, 12: 0.375, 16: 0.375}
    selection = runner._select_rung(
        throughput, wsl_available_bytes=22 * 2**30
    )
    assert selection["selected_workers"] == 4
    throughput = {1: 0.10, 2: 0.20, 4: 0.40, 8: 0.80, 12: 1.60, 16: 3.20}
    selection = runner._select_rung(
        throughput, wsl_available_bytes=22634487808
    )
    assert selection["selected_workers"] == 8
    decisions = {row["workers"]: row for row in selection["rung_decisions"]}
    assert decisions[12]["reason"] == "memory_reserve_guard"


def test_eig_gate_records_failure_gracefully(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R412-abort lesson: an init-divergent variant must be a gate failure,
    not a crash."""

    def broken_build(_variant, *, seed, steps):
        raise RuntimeError("simulated init divergence")

    monkeypatch.setattr(runner, "_build_env", broken_build)
    gate = runner.eig_gate(
        {"variant_id": "out_Line_7_12", "kind": "outage", "line_idx": "Line_7_12"}
    )
    assert gate["passed"] is False
    assert gate["failure"] is not None
    assert gate["variant_id"] == "out_Line_7_12"
    assert isinstance(gate["tds_test_ok"], bool)
