from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from andes_rl_kundur.evaluation.eval_v2 import (
    EvaluationContractError,
    evaluate_trace_directory,
    main,
    render_markdown,
)

ROOT = Path(__file__).resolve().parents[1]


def _write_trace(
    root: Path,
    *,
    scenario: str,
    controller: str,
    differential_amplitude: float,
    q_values: list[float] | None = None,
    completed: bool = True,
    location: str = "fixture",
    sign: str = "positive",
    severity: str = "moderate",
) -> None:
    q = q_values or [0.0, 0.0, 0.0, 0.0]
    traces = []
    for step, q_value in enumerate(q):
        amplitude = float(differential_amplitude)
        raw_coordinate = q_value / 0.25
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
                "freq_hz_physical": [
                    60.0 + amplitude,
                    60.0 + amplitude,
                    60.0 - amplitude,
                    60.0 - amplitude,
                ],
                "r278_q": q_value,
                "r278_raw_z": [
                    raw_coordinate,
                    raw_coordinate,
                    -raw_coordinate,
                    -raw_coordinate,
                ],
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
        "location": location,
        "sign": sign,
        "severity": severity,
        "completed": completed,
        "tds_failed": False,
        "n_steps": len(traces),
        "requested_steps": len(traces),
        "metric_frequency_basis": "andes_physical_hz",
        "andes_nominal_frequency_hz": 60.0,
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


def _rewrite_trace(path: Path, mutate: object) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutate(payload)  # type: ignore[operator]
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

    assert scorecard["validity"]["diagnostic_pass"] is True
    assert scorecard["validity"]["input_integrity"]["sidecar_sha256"]["verified_count"] == 4
    assert scorecard["contract"]["frequency_basis"] == "andes_physical_hz"
    assert scorecard["contract"]["no_composite_score_or_rank"] is True
    assert scorecard["contract"]["metric_roles"] == {
        "registered_co_primary": [
            "normalized_sync_loss_hz2",
            "fast_inter_area_iae_hz_s",
        ],
        "exploratory_physical": [
            "first_3s_common_iae_hz_s",
            "full_inter_area_iae_hz_s",
            "vsg_mean_iae_hz_s",
            "final_window_common_abs_mean_hz",
            "worst_bus_peak_abs_hz",
            "max_abs_rocof_hz_s",
            "secondary_3_to_10s_common_peak_abs_hz",
            "secondary_3_to_10s_inter_area_rms_hz",
        ],
        "legacy_compatibility": ["paper_cum_rf_sum_hz2"],
    }
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
    q_limit = np.float32(0.25)
    genuine_overrun = float(q_limit) + 2.0 * float(np.spacing(q_limit))
    for controller, q_values in (
        ("q0", [0.0, 0.0, 0.0, 0.0]),
        ("candidate", [0.0, genuine_overrun, 0.0, 0.0]),
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
    )

    assert scorecard["validity"]["diagnostic_pass"] is False
    assert scorecard["validity"]["execution_contract"]["violation_count"] >= 1
    assert "diagnostic_only" in scorecard["validity"]["interpretation"]


def test_eval_v2_uses_the_fixed_float32_representation_rule_without_claiming_evidence(
    tmp_path: Path,
) -> None:
    traces = tmp_path / "traces"
    traces.mkdir()
    for controller, q_values in (
        ("q0", [0.0, 0.0, 0.0, 0.0]),
        ("candidate", [0.0, 0.2500000074505806, 0.0, 0.0]),
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
    )

    assert scorecard["schema_version"] == 2
    assert scorecard["validity"]["diagnostic_pass"] is True
    assert scorecard["validity"]["input_integrity"]["pass"] is True
    assert scorecard["validity"]["execution_contract"]["pass"] is True
    assert "evidence_eligible" not in scorecard["validity"]
    assert scorecard["evidence_status"] == {
        "status": "EXTERNAL_AUTHORITY_REQUIRED",
        "eligible": None,
        "authority": "claim/feed/verdict ledger outside EVAL-v2",
    }
    assert scorecard["contract"]["action_audit_policy"] == {
        "representation": "float32",
        "q_limit_tolerance_rule": "spacing(float32(abs(limit)))",
        "override_allowed": False,
    }


def test_eval_v2_exposes_projection_nullspace_and_cancellation_diagnostics(
    tmp_path: Path,
) -> None:
    traces = tmp_path / "traces"
    traces.mkdir()
    _write_trace(
        traces,
        scenario="s1",
        controller="q0",
        differential_amplitude=1.0,
    )
    _write_trace(
        traces,
        scenario="s1",
        controller="shared_s17",
        differential_amplitude=0.8,
        q_values=[0.0, 0.0, 0.25, 0.0],
    )

    def add_projected_votes(payload: dict[str, object]) -> None:
        rows = payload["traces"]  # type: ignore[index]
        rows[0]["r278_raw_z"] = [0.95, 0.95, 0.95, 0.95]
        rows[1]["r278_raw_z"] = [-0.95, -0.95, -0.95, -0.95]
        rows[2]["r278_raw_z"] = [1.0, 1.0, -1.0, -1.0]

    _rewrite_trace(traces / "s1__shared_s17.json", add_projected_votes)

    scorecard = evaluate_trace_directory(traces, bootstrap_resamples=100)

    diagnostics = scorecard["controllers"]["shared_s17"]["action_diagnostics"]
    assert diagnostics["raw_same_sign_saturation_cancel_fraction"]["mean"] == pytest.approx(
        2.0 / 3.0
    )
    assert diagnostics["raw_nullspace_energy_fraction_mean"]["mean"] == pytest.approx(2.0 / 3.0)
    assert diagnostics["executed_q_abs_mean_normalized"]["mean"] == pytest.approx(1.0 / 3.0)
    assert scorecard["contract"]["projection_diagnostic_policy"] == {
        "analysis_class": "exploratory_post_hoc",
        "scope": "active_window",
        "same_sign_saturation_abs_raw_threshold": 0.9,
        "near_zero_executed_q_fraction_of_limit": 0.1,
    }


def test_eval_v2_stratifies_family_effects_by_scenario_metadata(
    tmp_path: Path,
) -> None:
    traces = tmp_path / "traces"
    traces.mkdir()
    for scenario, sign in (("negative_case", "negative"), ("positive_case", "positive")):
        _write_trace(
            traces,
            scenario=scenario,
            controller="q0",
            differential_amplitude=2.0,
            location="PQ_0",
            sign=sign,
            severity="edge",
        )
        for seed in (17, 53):
            _write_trace(
                traces,
                scenario=scenario,
                controller=f"centralized_s{seed}",
                differential_amplitude=1.0,
                location="PQ_0",
                sign=sign,
                severity="edge",
            )
            _write_trace(
                traces,
                scenario=scenario,
                controller=f"shared_s{seed}",
                differential_amplitude=2.0 if sign == "negative" else 1.0,
                location="PQ_0",
                sign=sign,
                severity="edge",
            )

    def add_cancelled_votes(payload: dict[str, object]) -> None:
        for row in payload["traces"][:3]:  # type: ignore[index]
            row["r278_raw_z"] = [0.95, 0.95, 0.95, 0.95]

    for seed in (17, 53):
        _rewrite_trace(
            traces / f"negative_case__shared_s{seed}.json",
            add_cancelled_votes,
        )

    scorecard = evaluate_trace_directory(traces, bootstrap_resamples=100)

    stratified = scorecard["stratified_effects"]
    assert stratified["analysis_class"] == "exploratory_post_hoc"
    negative = stratified["dimensions"]["sign"]["groups"]["negative"]
    positive = stratified["dimensions"]["sign"]["groups"]["positive"]
    negative_shared = negative["comparisons"]["shared_minus_baseline"]["metrics"][
        "normalized_sync_loss_hz2"
    ]
    positive_shared = positive["comparisons"]["shared_minus_baseline"]["metrics"][
        "normalized_sync_loss_hz2"
    ]
    assert negative_shared["ratio_of_means_percent"] == pytest.approx(0.0)
    assert negative_shared["scenario_improvement_count"] == 0
    assert positive_shared["ratio_of_means_percent"] == pytest.approx(-75.0)
    assert positive_shared["scenario_improvement_count"] == 1
    assert scorecard["source"]["scenario_metadata"]["negative_case"] == {
        "location": "PQ_0",
        "sign": "negative",
        "severity": "edge",
    }
    negative_shared_action = scorecard["stratified_action_diagnostics"]["dimensions"]["sign"][
        "groups"
    ]["negative"]["families"]["shared"]["metrics"]
    positive_shared_action = scorecard["stratified_action_diagnostics"]["dimensions"]["sign"][
        "groups"
    ]["positive"]["families"]["shared"]["metrics"]
    assert negative_shared_action["raw_same_sign_saturation_cancel_fraction"][
        "mean"
    ] == pytest.approx(1.0)
    assert positive_shared_action["raw_same_sign_saturation_cancel_fraction"][
        "mean"
    ] == pytest.approx(0.0)
    report = render_markdown(scorecard)
    assert "Formal evidence eligibility: **EXTERNAL AUTHORITY REQUIRED**" in report
    assert "## Projection and training-seed diagnostics" in report
    assert "Same-sign cancellation" in report
    assert "## Retained worst cases" in report
    assert "## Exploratory scenario strata" in report
    assert "`sign=negative`" in report


def test_eval_v2_requires_provenance_and_input_hash_sidecars(tmp_path: Path) -> None:
    traces = tmp_path / "traces"
    _write_paired_fixture(traces)
    for path in traces.glob("*.json"):
        _rewrite_trace(
            path,
            lambda payload: (
                payload.pop("formal_bank_sha256"),
                payload.pop("formal_seal_sha256"),
            ),
        )
        path.with_suffix(".json.sha256").unlink()

    scorecard = evaluate_trace_directory(traces, bootstrap_resamples=100)

    assert scorecard["validity"]["diagnostic_pass"] is False
    assert scorecard["validity"]["input_integrity"]["provenance_consistent"] is False
    assert scorecard["validity"]["input_integrity"]["sidecar_sha256"]["pass"] is False


def test_eval_v2_rejects_missing_storage_execution_telemetry(tmp_path: Path) -> None:
    traces = tmp_path / "traces"
    _write_paired_fixture(traces)
    path = traces / "s1__centralized_s17.json"

    def remove_storage(payload: dict[str, object]) -> None:
        for row in payload["traces"]:  # type: ignore[index]
            row.pop("bess_actual_power_system_pu")

    _rewrite_trace(path, remove_storage)

    scorecard = evaluate_trace_directory(traces, bootstrap_resamples=100)

    assert scorecard["validity"]["diagnostic_pass"] is False
    assert (
        scorecard["validity"]["execution_contract"]["failed_check_counts"][
            "missing_or_invalid_bess_actual_power_system_pu"
        ]
        == 1
    )


def test_eval_v2_rejects_missing_raw_vote_telemetry(tmp_path: Path) -> None:
    traces = tmp_path / "traces"
    _write_paired_fixture(traces)
    path = traces / "s1__centralized_s17.json"

    def remove_raw_vote(payload: dict[str, object]) -> None:
        payload["traces"][0].pop("r278_raw_z")  # type: ignore[index]

    _rewrite_trace(path, remove_raw_vote)

    scorecard = evaluate_trace_directory(traces, bootstrap_resamples=100)

    assert scorecard["validity"]["diagnostic_pass"] is False
    assert (
        scorecard["validity"]["execution_contract"]["failed_check_counts"][
            "missing_or_invalid_raw_vote"
        ]
        == 1
    )


def test_eval_v2_rejects_raw_votes_that_do_not_reconstruct_executed_q(
    tmp_path: Path,
) -> None:
    traces = tmp_path / "traces"
    _write_paired_fixture(traces)
    path = traces / "s1__centralized_s17.json"

    def corrupt_raw_projection(payload: dict[str, object]) -> None:
        payload["traces"][1]["r278_raw_z"] = [0.0, 0.0, 0.0, 0.0]  # type: ignore[index]

    _rewrite_trace(path, corrupt_raw_projection)

    scorecard = evaluate_trace_directory(traces, bootstrap_resamples=100)

    assert scorecard["validity"]["diagnostic_pass"] is False
    assert (
        scorecard["validity"]["execution_contract"]["failed_check_counts"][
            "raw_projection_mismatch"
        ]
        == 1
    )


def test_eval_v2_rejects_mismatched_paired_time_grids(tmp_path: Path) -> None:
    traces = tmp_path / "traces"
    _write_paired_fixture(traces)
    path = traces / "s1__centralized_s17.json"

    def stretch_time(payload: dict[str, object]) -> None:
        for index, row in enumerate(payload["traces"]):  # type: ignore[index]
            row["t"] = float(index * 2)

    _rewrite_trace(path, stretch_time)

    with pytest.raises(EvaluationContractError, match="time grid"):
        evaluate_trace_directory(traces, bootstrap_resamples=100)


def test_eval_v2_rejects_mismatched_paired_scenario_metadata(tmp_path: Path) -> None:
    traces = tmp_path / "traces"
    _write_paired_fixture(traces)
    path = traces / "s1__centralized_s17.json"

    def change_sign(payload: dict[str, object]) -> None:
        payload["sign"] = "negative"

    _rewrite_trace(path, change_sign)

    with pytest.raises(EvaluationContractError, match="scenario metadata sign"):
        evaluate_trace_directory(traces, bootstrap_resamples=100)


def test_eval_v2_requires_the_named_active_window_to_equal_three_seconds(
    tmp_path: Path,
) -> None:
    traces = tmp_path / "traces"
    _write_paired_fixture(traces)

    def shorten_grid(payload: dict[str, object]) -> None:
        for index, row in enumerate(payload["traces"]):  # type: ignore[index]
            row["t"] = float(index * 0.5)

    for path in traces.glob("*.json"):
        _rewrite_trace(path, shorten_grid)

    with pytest.raises(EvaluationContractError, match="exactly 3 seconds"):
        evaluate_trace_directory(traces, bootstrap_resamples=100)


def test_eval_v2_rejects_mislabeled_60_hz_trace(tmp_path: Path) -> None:
    traces = tmp_path / "traces"
    _write_paired_fixture(traces)
    path = traces / "s1__q0.json"

    def corrupt_absolute_frequency(payload: dict[str, object]) -> None:
        payload["traces"][0]["freq_hz_physical"][0] += 1.0  # type: ignore[index]

    _rewrite_trace(path, corrupt_absolute_frequency)

    with pytest.raises(EvaluationContractError, match="60-Hz"):
        evaluate_trace_directory(traces, bootstrap_resamples=100)


def test_eval_v2_cli_writes_auditable_json_markdown_and_hashes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
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
    cli_output = json.loads(capsys.readouterr().out)
    assert cli_output["evidence_status"]["status"] == "EXTERNAL_AUTHORITY_REQUIRED"


def test_eval_v2_thin_script_is_runnable_from_repo_root() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/eval_v2.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "EVAL-v2" in result.stdout


def test_eval_v2_markdown_leads_with_invalidity(tmp_path: Path) -> None:
    traces = tmp_path / "traces"
    traces.mkdir()
    q_limit = np.float32(0.25)
    genuine_overrun = float(q_limit) + 2.0 * float(np.spacing(q_limit))
    _write_trace(
        traces,
        scenario="s1",
        controller="q0",
        differential_amplitude=1.0,
        q_values=[0.0, genuine_overrun, 0.0, 0.0],
    )
    scorecard = evaluate_trace_directory(
        traces,
        bootstrap_resamples=100,
    )

    report = render_markdown(scorecard)

    assert "**INVALID / DIAGNOSTIC ONLY**" in report
    assert "No composite score or winner rank is produced." in report
    assert "Max abs(q)" in report
