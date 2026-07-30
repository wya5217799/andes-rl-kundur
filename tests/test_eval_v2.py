from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from andes_rl_kundur.evaluation.eval_v2 import (
    EvaluationContractError,
    evaluate_trace_directory,
    main,
    render_markdown,
)


def _write_trace(
    root: Path,
    *,
    scenario: str,
    controller: str,
    differential_amplitude: float,
    q_values: list[float] | None = None,
    completed: bool = True,
) -> None:
    q = q_values or [0.0, 0.0, 0.0, 0.0]
    traces = []
    for step, q_value in enumerate(q):
        amplitude = float(differential_amplitude)
        traces.append(
            {
                "step": step,
                "t": float(step),
                "delta_f_physical_hz": [
                    amplitude,
                    amplitude,
                    -amplitude,
                    -amplitude,
                ],
                "r278_q": q_value,
                "r278_raw_z": [q_value, q_value, -q_value, -q_value],
                "r278_residual_action_norm": [
                    q_value,
                    q_value,
                    -q_value,
                    -q_value,
                ],
                "r278_physical_m_residual_sum": 0.0,
                "bess_actual_power_system_pu": [0.0, 0.0, 0.0, 0.0],
                "bess_commanded_power_system_pu": [0.0, 0.0, 0.0, 0.0],
                "bess_requested_power_system_pu": [0.0, 0.0, 0.0, 0.0],
                "bess_soc": [0.5, 0.5, 0.5, 0.5],
                "bess_charge_energy_mwh_total": [0.0, 0.0, 0.0, 0.0],
                "bess_discharge_energy_mwh_total": [0.0, 0.0, 0.0, 0.0],
                "bess_constraint_violations": [],
                "bess_saturation_reasons": [[], [], [], []],
            }
        )
    payload = {
        "schema_version": 1,
        "scenario": scenario,
        "controller": controller,
        "completed": completed,
        "tds_failed": False,
        "n_steps": len(traces),
        "requested_steps": len(traces),
        "metric_frequency_basis": "andes_physical_hz",
        "formal_bank_sha256": "bank-hash",
        "formal_seal_sha256": "seal-hash",
        "controller_config": {
            "area_residual": {
                "active_steps": 3,
                "q_max": 0.25,
                "q_slew_max": 0.25,
            }
        },
        "traces": traces,
    }
    path = root / f"{scenario}__{controller}.json"
    data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    path.write_bytes(data)
    path.with_suffix(".json.sha256").write_text(
        f"{hashlib.sha256(data).hexdigest()}  {path.name}\n",
        encoding="utf-8",
    )


def _write_paired_fixture(root: Path) -> None:
    root.mkdir()
    for scenario, baseline_amplitude, candidate_amplitude in (
        ("s1", 2.0, 1.0),
        ("s2", 4.0, 2.0),
    ):
        _write_trace(
            root,
            scenario=scenario,
            controller="q0",
            differential_amplitude=baseline_amplitude,
        )
        _write_trace(
            root,
            scenario=scenario,
            controller="centralized_s17",
            differential_amplitude=candidate_amplitude,
            q_values=[0.0, 0.1, 0.1, 0.0],
        )


def test_eval_v2_rejects_incomplete_traces_before_statistics(tmp_path: Path) -> None:
    traces = tmp_path / "traces"
    traces.mkdir()
    _write_trace(
        traces,
        scenario="s1",
        controller="q0",
        differential_amplitude=1.0,
        completed=False,
    )

    with pytest.raises(EvaluationContractError, match="not completed"):
        evaluate_trace_directory(traces, bootstrap_resamples=100)


def test_eval_v2_emits_physical_paired_tail_and_legacy_compatibility(
    tmp_path: Path,
) -> None:
    traces = tmp_path / "traces"
    _write_paired_fixture(traces)

    scorecard = evaluate_trace_directory(
        traces,
        baseline="q0",
        bootstrap_resamples=200,
        bootstrap_seed=7,
        tail_fraction=0.5,
    )

    assert scorecard["validity"]["overall_pass"] is True
    assert scorecard["validity"]["sidecar_sha256"]["verified_count"] == 4
    assert scorecard["contract"]["frequency_basis"] == "andes_physical_hz"
    assert scorecard["contract"]["no_composite_score_or_rank"] is True
    assert "composite_score" not in scorecard

    baseline = scorecard["controllers"]["q0"]
    candidate = scorecard["controllers"]["centralized_s17"]
    assert baseline["metrics"]["normalized_sync_loss_hz2"]["mean"] == pytest.approx(10.0)
    assert candidate["metrics"]["normalized_sync_loss_hz2"]["mean"] == pytest.approx(2.5)
    assert baseline["legacy_compatibility"]["paper_cum_rf_sum_hz2"]["mean"] == (
        pytest.approx(-160.0)
    )
    assert scorecard["legacy_compatibility"]["identity"] == (
        "paper_cum_rf_sum_hz2 = -time_steps * agent_count * normalized_sync_loss_hz2"
    )

    paired = scorecard["paired_vs_baseline"]["contrasts"]["centralized_s17_minus_q0"]["endpoints"][
        "normalized_sync_loss_hz2"
    ]
    assert paired["ratio_of_means_percent"]["point"] == pytest.approx(-75.0)
    assert paired["scenario_improvement_count"] == 2
    assert paired["scenario_improvement_fraction"] == 1.0
    assert candidate["metrics"]["normalized_sync_loss_hz2"]["cvar_upper_tail"] == pytest.approx(4.0)


def test_eval_v2_keeps_action_validity_as_a_hard_gate(tmp_path: Path) -> None:
    traces = tmp_path / "traces"
    traces.mkdir()
    for controller, q_values in (
        ("q0", [0.0, 0.0, 0.0, 0.0]),
        ("candidate", [0.0, 0.250000005, 0.0, 0.0]),
    ):
        _write_trace(
            traces,
            scenario="s1",
            controller=controller,
            differential_amplitude=1.0,
            q_values=q_values,
        )

    scorecard = evaluate_trace_directory(
        traces,
        bootstrap_resamples=100,
        q_audit_tolerance=1e-9,
    )

    assert scorecard["validity"]["overall_pass"] is False
    assert scorecard["validity"]["evidence_eligible"] is False
    assert scorecard["validity"]["action_contract"]["violation_count"] >= 1
    assert "diagnostic_only" in scorecard["validity"]["interpretation"]


def test_eval_v2_cli_writes_auditable_json_markdown_and_hashes(
    tmp_path: Path,
) -> None:
    traces = tmp_path / "traces"
    output = tmp_path / "out"
    _write_paired_fixture(traces)

    exit_code = main(
        [
            "--trace-dir",
            str(traces),
            "--output-dir",
            str(output),
            "--bootstrap-resamples",
            "100",
            "--overwrite",
        ]
    )

    assert exit_code == 0
    json_path = output / "scorecard.json"
    markdown_path = output / "scorecard.md"
    assert json_path.is_file()
    assert markdown_path.is_file()
    assert json_path.with_suffix(".json.sha256").is_file()
    assert markdown_path.with_suffix(".md.sha256").is_file()
    persisted = json.loads(json_path.read_text(encoding="utf-8"))
    assert persisted["source"]["trace_count"] == 4
    assert "# EVAL-v2 objective scorecard" in markdown_path.read_text(encoding="utf-8")


def test_eval_v2_markdown_leads_with_invalidity(tmp_path: Path) -> None:
    traces = tmp_path / "traces"
    traces.mkdir()
    _write_trace(
        traces,
        scenario="s1",
        controller="q0",
        differential_amplitude=1.0,
        q_values=[0.0, 0.250000005, 0.0, 0.0],
    )
    scorecard = evaluate_trace_directory(
        traces,
        bootstrap_resamples=100,
        q_audit_tolerance=1e-9,
    )

    report = render_markdown(scorecard)

    assert "**INVALID / DIAGNOSTIC ONLY**" in report
    assert "No composite score or winner rank is produced." in report
    assert "Max abs(q)" in report
