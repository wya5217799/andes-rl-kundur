#!/usr/bin/env python3
"""Run the sealed R319 model-only observer-LQR synthesis gate.

Usage:
    python scripts/run_r319_observer_lqr.py prepare
    python scripts/run_r319_observer_lqr.py execute --expected-sha256 <seal>
    python scripts/run_r319_observer_lqr.py analyse --expected-sha256 <seal>

The script never imports ANDES and exposes no physical-run or EVAL command.
All synthesis rules, cases, thresholds, and comparison fields are sealed before
the first controller outcome is computed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from andes_rl_kundur.control.model_first_observer_lqr import (  # noqa: E402
    ObserverLqrDesign,
    delete_common_differential_markov_blocks,
    simulate_observer_lqr_feedback,
    synthesize_observer_lqr,
)
from andes_rl_kundur.control.model_first_offline_feedback import (  # noqa: E402
    FeedbackCase,
    FeedbackLimits,
    simulate_delayed_output_feedback,
)
from andes_rl_kundur.env.andes.model_first_contract import (  # noqa: E402
    active_power_incidence,
)
from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (  # noqa: E402
    StateSpaceRealization,
    enforce_spectral_radius,
    fit_era_realization,
    realization_from_dict,
    simulate_state_space,
)
from probes.r319_observer_lqr_validation import evaluate_observer_lqr  # noqa: E402

ROUND_ID = "R319"
QUESTION_ID = "Q-0074"
PARENT_MODEL = ROOT / "results/r316_dynamic_reduction/dynamic_model.json"
PARENT_ANALYSIS = ROOT / "results/r316_dynamic_reduction/analysis.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R319/observer_lqr_seal.json"
DEFAULT_OUT = ROOT / "results/r319_observer_lqr"
HORIZON_STEPS = 50
POINT_SOC = {"HS0": 0.41, "HS1": 0.51}
COORDINATES = ("common", "edge_0", "edge_1", "edge_2")


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _payload_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path_text(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _write_new_json(path: Path, payload: object) -> str:
    if path.exists() or path.with_suffix(path.suffix + ".sha256").exists():
        raise FileExistsError(f"create-only artifact already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    path.write_text(text, encoding="utf-8")
    digest = _sha256_file(path)
    path.with_suffix(path.suffix + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="ascii"
    )
    return digest


def _read_verified_json(
    path: Path,
    expected_sha256: str | None = None,
) -> tuple[dict[str, Any], str]:
    if not path.is_file():
        raise FileNotFoundError(path)
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not sidecar.is_file():
        raise FileNotFoundError(sidecar)
    digest = _sha256_file(path)
    sidecar_digest = sidecar.read_text(encoding="ascii").split()[0]
    if digest != sidecar_digest or (
        expected_sha256 is not None and digest != expected_sha256
    ):
        raise RuntimeError(f"hash mismatch for {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON artifact is not an object: {path}")
    return payload, digest


def build_contract() -> dict[str, Any]:
    """Return the exact prospective R319 synthesis and rejection contract."""

    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "model-only-delay-augmented-observer-lqr",
        "parent_round": "R316",
        "parent_claims": ["CLM-0790", "CLM-0795", "CLM-0800"],
        "sample_period_seconds": 0.2,
        "horizon_steps": HORIZON_STEPS,
        "coordinates": list(COORDINATES),
        "points": [
            {"name": name, "initial_soc": soc} for name, soc in POINT_SOC.items()
        ],
        "delay_augmentation": {
            "state": "z[k]=[x[k],y[k-1]]",
            "state_matrix": "[[A,0],[C,0]]",
            "input_matrix": "[[B],[D]]",
            "measurement_matrix": "[0,I]",
            "first_measurement": "zero",
            "initial_estimate": "zero",
            "first_command": "zero",
        },
        "controller": {
            "kind": "full-order-generalized-output-energy-discrete-LQR",
            "output_scale": "retained-model-development-pooled-RMS",
            "output_scale_floor_fraction": 0.05,
            "action_scale": "node-power-ceiling-divided-by-basis-column-maximum",
            "feedthrough_in_cost": True,
        },
        "observer": {
            "kind": "full-order-corrected-state-dual-discrete-Riccati",
            "disturbance_scale": 0.05,
            "measurement_fraction_of_output_scale": 0.01,
            "process_covariance_identity_floor": 1.0e-12,
            "initial_state": "zero",
        },
        "synthesis_count_per_point_and_arm": 1,
        "tuning_candidate_count": 0,
        "retained_arm": "unchanged-R316-order-10-realizations",
        "matched_baseline": {
            "single_factor": "delete-common-differential-transfer-blocks",
            "markov_horizon_steps": 25,
            "era_order": 10,
            "block_rows": 8,
            "block_columns": 8,
            "maximum_model_spectral_radius": 0.995,
            "executed_plant": "unchanged-full-retained-cross-R316-realization",
        },
        "development_shapes": {
            "impulse": [0.05],
            "triangle": [0.02, 0.04, 0.05, 0.04, 0.02],
        },
        "examination_shapes": {
            "bipolar": [0.05, 0.05, 0.0, -0.05, -0.05],
        },
        "development_case_count": 32,
        "examination_base_case_count": 16,
        "mismatch_mode_count": 5,
        "examination_case_count": 80,
        "mismatch_scale": 0.15,
        "mismatch_pointwise_ceiling": 0.20,
        "limits": asdict(FeedbackLimits()),
        "maximum_pole_radius": 0.995,
        "minimum_improvement": 0.02,
        "comparison_identifiability": {
            "decision": "ALLOW",
            "single_factor": "retain-versus-delete-named-transfer-blocks",
            "matched": [
                "full-retained-cross-executed-plant-models",
                "delivered-four-coordinate-delayed-measurement",
                "known-point-label",
                "four-coordinate-action-and-node-governor",
                "sample-timing-and-horizon",
                "model-order-and-one-synthesis-per-point",
                "zero-tuning-candidates",
                "disturbances-and-mismatch-transforms",
                "objective-and-metrics",
            ],
        },
        "classification": [
            "INVALID-OBSERVER-LQR",
            "OBSERVER-LQR-NO-GO",
            "OBSERVER-LQR-PASS",
        ],
        "eval": "NOT-APPLICABLE-MODEL-ONLY",
        "physical_execution_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }


def _disturbance(sequence: list[float], coordinate_index: int, sign: float) -> np.ndarray:
    values = np.zeros((HORIZON_STEPS, 4))
    values[: len(sequence), coordinate_index] = sign * np.asarray(sequence)
    return values


def _cases(shapes: dict[str, list[float]]) -> list[FeedbackCase]:
    cases: list[FeedbackCase] = []
    for point, initial_soc in POINT_SOC.items():
        for shape, sequence in shapes.items():
            for coordinate_index, coordinate in enumerate(COORDINATES):
                for sign_name, sign in (("positive", 1.0), ("negative", -1.0)):
                    cases.append(
                        FeedbackCase(
                            point=point,
                            name=f"{point}/{shape}/{coordinate}/{sign_name}",
                            disturbance=_disturbance(sequence, coordinate_index, sign),
                            initial_soc=initial_soc,
                        )
                    )
    return cases


def development_cases() -> list[FeedbackCase]:
    return _cases(build_contract()["development_shapes"])


def examination_cases() -> list[FeedbackCase]:
    return _cases(build_contract()["examination_shapes"])


def mismatch_transforms() -> dict[str, np.ndarray]:
    reflection = np.diag([1.0, -1.0, 1.0, -1.0])
    exchange = np.array(
        [
            [0.0, 1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )
    return {
        "nominal": np.zeros((4, 4)),
        "plus_scale": 0.15 * np.eye(4),
        "minus_scale": -0.15 * np.eye(4),
        "signed_reflection": 0.15 * reflection,
        "common_differential_exchange": 0.15 * exchange,
    }


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R319/plan.md",
        "question": ROOT / "memory/questions/Q-0074.md",
        "dynamic_model_claim": ROOT / "memory/claims/CLM-0790.md",
        "static_rejection_claim": ROOT / "memory/claims/CLM-0795.md",
        "cause_claim": ROOT / "memory/claims/CLM-0800.md",
        "parent_model": PARENT_MODEL,
        "parent_analysis": PARENT_ANALYSIS,
        "controller_module": SRC
        / "andes_rl_kundur/control/model_first_observer_lqr.py",
        "validation_probe": ROOT / "probes/r319_observer_lqr_validation.py",
        "adapter": Path(__file__).resolve(),
        "controller_tests": ROOT / "tests/test_model_first_observer_lqr.py",
        "validation_tests": ROOT / "tests/test_r319_observer_lqr_validation.py",
        "adapter_tests": ROOT / "tests/test_r319_observer_lqr.py",
    }


def _sources() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _path_text(path), "sha256": _sha256_file(path)}
        for name, path in _source_paths().items()
    }


def _load_parent() -> tuple[dict[str, Any], str, dict[str, Any], str]:
    model, model_digest = _read_verified_json(PARENT_MODEL)
    analysis, analysis_digest = _read_verified_json(PARENT_ANALYSIS)
    if (
        model.get("round") != "R316"
        or model.get("question") != "Q-0071"
        or model.get("R316_holdout_accessed") is not False
        or set(model.get("points", {})) != set(POINT_SOC)
        or analysis.get("classification") != "DYNAMIC-REDUCTION-PASS"
        or analysis.get("dynamic_model_sha256") != model_digest
        or analysis.get("training_authorized") is not False
    ):
        raise RuntimeError("R316 parent authority contract mismatch")
    return model, model_digest, analysis, analysis_digest


def prepare(seal_path: Path) -> str:
    _model, model_digest, _analysis, analysis_digest = _load_parent()
    contract = build_contract()
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": _payload_sha256(contract),
        "parent": {
            "dynamic_model": {"path": _path_text(PARENT_MODEL), "sha256": model_digest},
            "analysis": {"path": _path_text(PARENT_ANALYSIS), "sha256": analysis_digest},
        },
        "sources": _sources(),
    }
    digest = _write_new_json(seal_path, seal)
    print(f"seal_sha256={digest}", flush=True)
    return digest


def _load_seal(path: Path, expected: str) -> tuple[dict[str, Any], str]:
    seal, digest = _read_verified_json(path, expected)
    contract = build_contract()
    if (
        seal.get("round") != ROUND_ID
        or seal.get("question") != QUESTION_ID
        or seal.get("contract") != contract
        or seal.get("contract_payload_sha256") != _payload_sha256(contract)
    ):
        raise RuntimeError("R319 seal contract drift")
    _model, model_digest, _analysis, analysis_digest = _load_parent()
    if seal.get("parent") != {
        "dynamic_model": {"path": _path_text(PARENT_MODEL), "sha256": model_digest},
        "analysis": {"path": _path_text(PARENT_ANALYSIS), "sha256": analysis_digest},
    }:
        raise RuntimeError("R319 sealed parent drift")
    for name, entry in seal["sources"].items():
        if _sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"R319 sealed source drift for {name}")
    return seal, digest


def _models(
    model: dict[str, Any],
) -> tuple[dict[str, StateSpaceRealization], dict[str, np.ndarray]]:
    points = model.get("points")
    if not isinstance(points, dict) or set(points) != set(POINT_SOC):
        raise RuntimeError("R316 point set mismatch")
    retained = {
        name: realization_from_dict(entry["realization"])
        for name, entry in points.items()
    }
    markov = {
        name: np.asarray(entry["markov_parameters"], dtype=float)
        for name, entry in points.items()
    }
    if not all(
        retained[name].state_matrix.shape == (10, 10)
        and retained[name].input_matrix.shape == (10, 4)
        and retained[name].output_matrix.shape == (4, 10)
        and retained[name].feedthrough_matrix.shape == (4, 4)
        and markov[name].shape == (25, 4, 4)
        and np.all(np.isfinite(markov[name]))
        for name in POINT_SOC
    ):
        raise RuntimeError("R316 realization or Markov matrix contract mismatch")
    return retained, markov


def _cross_deleted_models(markov: dict[str, np.ndarray]) -> dict[str, StateSpaceRealization]:
    contract = build_contract()["matched_baseline"]
    result: dict[str, StateSpaceRealization] = {}
    for point, tensor in markov.items():
        deleted = delete_common_differential_markov_blocks(tensor)
        realization = fit_era_realization(
            deleted,
            order=contract["era_order"],
            block_rows=contract["block_rows"],
            block_columns=contract["block_columns"],
        )
        if realization.spectral_radius > contract["maximum_model_spectral_radius"]:
            realization = enforce_spectral_radius(
                realization,
                maximum_radius=contract["maximum_model_spectral_radius"],
            )
        result[point] = realization
    return result


def _output_scales(
    retained: dict[str, StateSpaceRealization],
) -> dict[str, np.ndarray]:
    fraction = build_contract()["controller"]["output_scale_floor_fraction"]
    scales: dict[str, np.ndarray] = {}
    for point, realization in retained.items():
        responses = [
            simulate_state_space(realization, case.disturbance)
            for case in development_cases()
            if case.point == point
        ]
        pooled = np.concatenate(responses, axis=0)
        rms = np.sqrt(np.mean(np.square(pooled), axis=0))
        floor = fraction * float(np.max(rms))
        scales[point] = np.maximum(rms, floor)
        if not np.all(np.isfinite(scales[point])) or np.any(scales[point] <= 0.0):
            raise RuntimeError("retained-model development output scale is invalid")
    return scales


def _action_scales(limits: FeedbackLimits) -> np.ndarray:
    basis = np.column_stack((np.ones(4), active_power_incidence()))
    scales = limits.node_power / np.max(np.abs(basis), axis=0)
    if scales.shape != (4,) or np.any(scales <= 0.0):
        raise RuntimeError("coordinate action scale is invalid")
    return scales


def _designs(
    models: dict[str, StateSpaceRealization],
    output_scales: dict[str, np.ndarray],
    action_scales: np.ndarray,
) -> dict[str, ObserverLqrDesign]:
    observer = build_contract()["observer"]
    return {
        point: synthesize_observer_lqr(
            realization,
            output_scales=output_scales[point],
            action_scales=action_scales,
            disturbance_scale=observer["disturbance_scale"],
            measurement_fraction=observer["measurement_fraction_of_output_scale"],
        )
        for point, realization in models.items()
    }


def _not_run_summary(reason: str) -> dict[str, object]:
    return {
        "case_count": 0,
        "finite": True,
        "constraint_violation_count": 0,
        "innovation_energy_ratios": [],
        "energy_ratios_to_zero": [],
        "not_run_reason": reason,
    }


def _evaluate_cases(
    plants: dict[str, StateSpaceRealization],
    designs: dict[str, ObserverLqrDesign],
    cases: list[FeedbackCase],
    *,
    limits: FeedbackLimits,
    transforms: dict[str, np.ndarray],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    rows: list[dict[str, object]] = []
    energy_ratios: list[float] = []
    innovation_ratios: list[float] = []
    finite = True
    violations = 0
    for case in cases:
        plant = plants[case.point]
        design = designs[case.point]
        for mismatch_name, mismatch in transforms.items():
            zero = simulate_delayed_output_feedback(
                plant,
                case.disturbance,
                gain=np.zeros((4, 4)),
                initial_soc=case.initial_soc,
                limits=limits,
                mismatch_transform=mismatch,
            )
            controlled = simulate_observer_lqr_feedback(
                plant,
                case.disturbance,
                design=design,
                initial_soc=case.initial_soc,
                limits=limits,
                mismatch_transform=mismatch,
            )
            denominator = max(zero.output_energy, np.finfo(float).tiny)
            energy_ratio = controlled.output_energy / denominator
            innovation_ratio = controlled.innovation_energy / denominator
            node_deltas = np.vstack(
                (controlled.node_actions[:1], np.diff(controlled.node_actions, axis=0))
            )
            row = {
                "case": case.name,
                "point": case.point,
                "mismatch": mismatch_name,
                "output_energy": controlled.output_energy,
                "zero_control_output_energy": zero.output_energy,
                "output_energy_ratio_to_zero": energy_ratio,
                "innovation_energy_ratio_to_zero": innovation_ratio,
                "coordinate_action_energy": controlled.coordinate_action_energy,
                "maximum_node_power": float(np.max(np.abs(controlled.node_actions))),
                "maximum_node_ramp": float(np.max(np.abs(node_deltas))),
                "minimum_soc": float(np.min(controlled.soc)),
                "maximum_soc": float(np.max(controlled.soc)),
                "governor_intervention_count": controlled.governor_intervention_count,
                "constraint_violation_count": controlled.constraint_violation_count,
            }
            row_finite = all(
                np.isfinite(value)
                for key, value in row.items()
                if key not in {"case", "point", "mismatch"}
            )
            finite = finite and row_finite
            violations += controlled.constraint_violation_count
            energy_ratios.append(energy_ratio)
            innovation_ratios.append(innovation_ratio)
            rows.append(row)
    return (
        {
            "case_count": len(rows),
            "finite": finite,
            "constraint_violation_count": violations,
            "innovation_energy_ratios": innovation_ratios,
            "energy_ratios_to_zero": energy_ratios,
        },
        rows,
    )


def _calculate(model: dict[str, Any]) -> dict[str, Any]:
    contract = build_contract()
    limits = FeedbackLimits(**contract["limits"])
    retained, markov = _models(model)
    arm_models = {
        "retained_cross": retained,
        "cross_deleted": _cross_deleted_models(markov),
    }
    output_scales = _output_scales(retained)
    action_scales = _action_scales(limits)
    arms: dict[str, dict[str, object]] = {}
    rows: dict[str, dict[str, list[dict[str, object]]]] = {}
    arm_designs: dict[str, dict[str, ObserverLqrDesign]] = {}
    for name, models in arm_models.items():
        try:
            designs = _designs(models, output_scales, action_scales)
        except ValueError as exc:
            arms[name] = {
                "synthesis_feasible": False,
                "synthesis_error": str(exc),
                "point_designs": {},
                "development": _not_run_summary("synthesis-failed"),
                "examination": _not_run_summary("development-gate-failed"),
            }
            rows[name] = {"development": [], "examination": []}
            continue
        arm_designs[name] = designs
        development, development_rows = _evaluate_cases(
            retained,
            designs,
            development_cases(),
            limits=limits,
            transforms={"nominal": np.zeros((4, 4))},
        )
        arms[name] = {
            "synthesis_feasible": True,
            "point_designs": {
                point: {
                    "controller_pole_radius": design.controller_pole_radius,
                    "observer_pole_radius": design.observer_pole_radius,
                    "feedback_gain": design.feedback_gain.tolist(),
                    "filter_gain": design.filter_gain.tolist(),
                    "output_scales": design.output_scales.tolist(),
                    "action_scales": design.action_scales.tolist(),
                }
                for point, design in designs.items()
            },
            "development": development,
        }
        rows[name] = {"development": development_rows, "examination": []}

    development_pass = all(
        name in arm_designs
        and all(
            design.controller_pole_radius <= contract["maximum_pole_radius"]
            and design.observer_pole_radius <= contract["maximum_pole_radius"]
            for design in arm_designs[name].values()
        )
        and arms[name]["development"]["finite"] is True  # type: ignore[index]
        and arms[name]["development"]["constraint_violation_count"] == 0  # type: ignore[index]
        for name in ("retained_cross", "cross_deleted")
    )
    for name in ("retained_cross", "cross_deleted"):
        if not development_pass:
            arms[name]["examination"] = _not_run_summary(  # type: ignore[index]
                "development-gate-failed"
            )
            continue
        examination, examination_rows = _evaluate_cases(
            retained,
            arm_designs[name],
            examination_cases(),
            limits=limits,
            transforms=mismatch_transforms(),
        )
        arms[name]["examination"] = examination  # type: ignore[index]
        rows[name]["examination"] = examination_rows

    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "output_scales": {name: value.tolist() for name, value in output_scales.items()},
        "action_scales": action_scales.tolist(),
        "arms": arms,
        "cases": rows,
        "development_gate_passed": development_pass,
        "eval_status": "NOT-APPLICABLE-MODEL-ONLY",
        "physical_execution_performed": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }


def execute(seal_path: Path, expected: str, out_dir: Path) -> str:
    seal, seal_digest = _load_seal(seal_path, expected)
    model, model_digest, _analysis, _analysis_digest = _load_parent()
    first = _calculate(model)
    second = _calculate(model)
    deterministic = _payload_sha256(first) == _payload_sha256(second)
    examination_was_run = any(
        arm["examination"]["case_count"] > 0 for arm in first["arms"].values()
    )
    expected_examination = bool(first["development_gate_passed"])
    first.update(
        {
            "schema_version": 1,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "contract_payload_sha256": seal["contract_payload_sha256"],
            "parent_model_sha256": model_digest,
            "validity_guards": {
                "sealed_source_identity": True,
                "matrix_contract": True,
                "deterministic_replay": deterministic,
                "case_contract": bool(
                    len(development_cases()) == 32
                    and len(examination_cases()) == 16
                    and len(mismatch_transforms()) == 5
                ),
                "comparison_contract": bool(
                    seal["contract"]["comparison_identifiability"]["decision"]
                    == "ALLOW"
                    and seal["contract"]["tuning_candidate_count"] == 0
                ),
                "cross_deletion_contract": all(
                    np.allclose(
                        delete_common_differential_markov_blocks(tensor)[:, 0, 1:],
                        0.0,
                    )
                    and np.allclose(
                        delete_common_differential_markov_blocks(tensor)[:, 1:, 0],
                        0.0,
                    )
                    for tensor in _models(model)[1].values()
                ),
                "no_examination_on_development_failure": bool(
                    examination_was_run == expected_examination
                ),
                "eval_not_run": bool(
                    first["eval_status"] == "NOT-APPLICABLE-MODEL-ONLY"
                    and first["physical_execution_performed"] is False
                ),
            },
        }
    )
    digest = _write_new_json(out_dir / "controller_result.json", first)
    print(f"controller_result_sha256={digest}", flush=True)
    return digest


def analyse(seal_path: Path, expected: str, out_dir: Path) -> str:
    seal, seal_digest = _load_seal(seal_path, expected)
    result, result_digest = _read_verified_json(out_dir / "controller_result.json")
    if (
        result.get("seal_sha256") != seal_digest
        or result.get("contract_payload_sha256") != seal["contract_payload_sha256"]
    ):
        raise RuntimeError("R319 result provenance mismatch")
    analysis = evaluate_observer_lqr(result)
    analysis.update(
        {
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "controller_result_sha256": result_digest,
            "contract_payload_sha256": seal["contract_payload_sha256"],
        }
    )
    analysis_digest = _write_new_json(out_dir / "analysis.json", analysis)
    provenance = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal": {"path": _path_text(seal_path), "sha256": seal_digest},
        "controller_result": {
            "path": _path_text(out_dir / "controller_result.json"),
            "sha256": result_digest,
        },
        "analysis": {
            "path": _path_text(out_dir / "analysis.json"),
            "sha256": analysis_digest,
        },
        "parent": seal["parent"],
        "physical_execution_performed": False,
        "eval_status": "NOT-APPLICABLE-MODEL-ONLY",
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }
    provenance_digest = _write_new_json(out_dir / "provenance.json", provenance)
    print(f"classification={analysis['classification']}", flush=True)
    print(f"analysis_sha256={analysis_digest}", flush=True)
    print(f"provenance_sha256={provenance_digest}", flush=True)
    return analysis_digest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "execute", "analyse"))
    parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--expected-sha256")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "prepare":
        if args.expected_sha256 is not None:
            raise SystemExit("prepare does not accept --expected-sha256")
        prepare(args.seal)
        return 0
    if not args.expected_sha256:
        raise SystemExit(f"{args.command} requires --expected-sha256")
    if args.command == "execute":
        execute(args.seal, args.expected_sha256, args.out)
    else:
        analyse(args.seal, args.expected_sha256, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
