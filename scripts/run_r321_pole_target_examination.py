#!/usr/bin/env python3
"""Run the sealed R321 exact fixed pole-target model-only examination.

Usage:
    python scripts/run_r321_pole_target_examination.py prepare
    python scripts/run_r321_pole_target_examination.py execute --expected-sha256 <seal>
    python scripts/run_r321_pole_target_examination.py analyse --expected-sha256 <seal>

The adapter never imports ANDES and exposes no physical-run or EVAL command.
Targets, scales, cases, limits, comparison, and gates are sealed before the
first controller outcome is computed.
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
)
from andes_rl_kundur.control.model_first_offline_feedback import (  # noqa: E402
    FeedbackCase,
    FeedbackLimits,
    simulate_delayed_output_feedback,
)
from andes_rl_kundur.control.model_first_pole_target import (  # noqa: E402
    FixedPoleTargetDesign,
    synthesize_fixed_pole_target,
)
from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (  # noqa: E402
    StateSpaceRealization,
    enforce_spectral_radius,
    fit_era_realization,
    realization_from_dict,
)
from probes.r321_pole_target_validation import (  # noqa: E402
    evaluate_pole_target_examination,
)

ROUND_ID = "R321"
QUESTION_ID = "Q-0076"
R316_MODEL = ROOT / "results/r316_dynamic_reduction/dynamic_model.json"
R316_ANALYSIS = ROOT / "results/r316_dynamic_reduction/analysis.json"
R319_SEAL = ROOT / "memory/rounds/R319/observer_lqr_seal.json"
R319_RESULT = ROOT / "results/r319_observer_lqr/controller_result.json"
R319_ANALYSIS = ROOT / "results/r319_observer_lqr/analysis.json"
R319_PROVENANCE = ROOT / "results/r319_observer_lqr/provenance.json"
R320_SEAL = ROOT / "memory/rounds/R320/pole_cause_seal.json"
R320_DIAGNOSTIC = ROOT / "results/r320_pole_cause/diagnostic.json"
R320_ANALYSIS = ROOT / "results/r320_pole_cause/analysis.json"
R320_PROVENANCE = ROOT / "results/r320_pole_cause/provenance.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R321/pole_target_examination_seal.json"
DEFAULT_OUT = ROOT / "results/r321_pole_target_examination"
HORIZON_STEPS = 50
POINT_SOC = {"HS0": 0.41, "HS1": 0.51}
COORDINATES = ("common", "edge_0", "edge_1", "edge_2")
ARMS = ("retained_cross", "cross_deleted")
OUTPUT_SCALES = {
    "HS0": [
        0.0002668112041645563,
        0.00015882926554077416,
        0.00019288206508276265,
        0.0002124274132893341,
    ],
    "HS1": [
        0.00025989821599602683,
        0.00014880082973969276,
        0.00018244950507686816,
        0.00020106658488483798,
    ],
}
ACTION_SCALES = [0.36, 0.36, 0.36, 0.36]


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
    """Return the exact prospective R321 execution and rejection contract."""

    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "exact-fixed-pole-target-model-only-examination",
        "parent_rounds": ["R316", "R319", "R320"],
        "parent_claims": ["CLM-0790", "CLM-0805", "CLM-0810"],
        "sample_period_seconds": 0.2,
        "horizon_steps": HORIZON_STEPS,
        "coordinates": list(COORDINATES),
        "points": [
            {"name": name, "initial_soc": soc} for name, soc in POINT_SOC.items()
        ],
        "controller_target_poles": np.linspace(0.90, 0.98, 14).tolist(),
        "observer_target_poles": (
            [0.0] * 4 + np.linspace(0.80, 0.94, 10).tolist()
        ),
        "placement_method": "YT",
        "placement_relative_tolerance": 1.0e-6,
        "placement_maximum_iterations": 100,
        "placement_target_tolerance": 1.0e-8,
        "controller_target_radius": 0.98,
        "observer_target_radius": 0.94,
        "placement_call_count_per_point_and_arm": 1,
        "tuning_candidate_count": 0,
        "output_scales": {key: list(value) for key, value in OUTPUT_SCALES.items()},
        "action_scales": list(ACTION_SCALES),
        "delay_augmentation": {
            "state": "z[k]=[x[k],y[k-1]]",
            "state_matrix": "[[A,0],[C,0]]",
            "input_matrix": "[[B],[D]]",
            "measurement_matrix": "[0,I]",
            "first_measurement": "zero",
            "initial_estimate": "zero",
            "first_command": "zero",
        },
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
        "minimum_improvement": 0.02,
        "comparison_identifiability": {
            "decision": "ALLOW",
            "scientific_object": (
                "one-exact-fixed-pole-targeted-observer-feedback-construction"
            ),
            "single_factor": "retain-versus-delete-named-transfer-blocks",
            "estimand": "finite-bank-normalized-output-energy-value",
            "matched": [
                "full-retained-cross-executed-plant-models",
                "delivered-four-coordinate-delayed-measurement",
                "known-point-label",
                "four-coordinate-action-and-node-governor",
                "sample-timing-and-horizon",
                "pole-targets-method-tolerances-and-one-call-budget",
                "model-order-and-zero-tuning-candidates",
                "disturbances-and-mismatch-transforms",
                "objective-and-metrics",
            ],
        },
        "classification": [
            "INVALID-POLE-TARGET-EXAMINATION",
            "POLE-TARGET-NO-GO",
            "POLE-TARGET-PASS",
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
        "plan": ROOT / "memory/rounds/R321/plan.md",
        "question": ROOT / "memory/questions/Q-0076.md",
        "dynamic_model_claim": ROOT / "memory/claims/CLM-0790.md",
        "observer_lqr_claim": ROOT / "memory/claims/CLM-0805.md",
        "pole_target_claim": ROOT / "memory/claims/CLM-0810.md",
        "r316_model": R316_MODEL,
        "r316_analysis": R316_ANALYSIS,
        "r319_seal": R319_SEAL,
        "r319_result": R319_RESULT,
        "r319_analysis": R319_ANALYSIS,
        "r319_provenance": R319_PROVENANCE,
        "r320_seal": R320_SEAL,
        "r320_diagnostic": R320_DIAGNOSTIC,
        "r320_analysis": R320_ANALYSIS,
        "r320_provenance": R320_PROVENANCE,
        "observer_feedback_module": SRC
        / "andes_rl_kundur/control/model_first_observer_lqr.py",
        "pole_target_module": SRC
        / "andes_rl_kundur/control/model_first_pole_target.py",
        "validation_probe": ROOT / "probes/r321_pole_target_validation.py",
        "adapter": Path(__file__).resolve(),
        "controller_tests": ROOT / "tests/test_model_first_pole_target.py",
        "validation_tests": ROOT / "tests/test_r321_pole_target_validation.py",
        "adapter_tests": ROOT / "tests/test_r321_pole_target_examination.py",
    }


def _sources() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _path_text(path), "sha256": _sha256_file(path)}
        for name, path in _source_paths().items()
    }


def _load_parents() -> tuple[dict[str, Any], dict[str, dict[str, str]]]:
    r316_model, r316_model_digest = _read_verified_json(R316_MODEL)
    r316_analysis, r316_analysis_digest = _read_verified_json(R316_ANALYSIS)
    r319_seal, r319_seal_digest = _read_verified_json(R319_SEAL)
    r319_result, r319_result_digest = _read_verified_json(R319_RESULT)
    r319_analysis, r319_analysis_digest = _read_verified_json(R319_ANALYSIS)
    r319_provenance, r319_provenance_digest = _read_verified_json(R319_PROVENANCE)
    r320_seal, r320_seal_digest = _read_verified_json(R320_SEAL)
    r320_diagnostic, r320_diagnostic_digest = _read_verified_json(R320_DIAGNOSTIC)
    r320_analysis, r320_analysis_digest = _read_verified_json(R320_ANALYSIS)
    r320_provenance, r320_provenance_digest = _read_verified_json(R320_PROVENANCE)
    if (
        r316_model.get("round") != "R316"
        or set(r316_model.get("points", {})) != set(POINT_SOC)
        or r316_analysis.get("classification") != "DYNAMIC-REDUCTION-PASS"
        or r316_analysis.get("dynamic_model_sha256") != r316_model_digest
        or r319_seal.get("round") != "R319"
        or r319_result.get("seal_sha256") != r319_seal_digest
        or r319_analysis.get("classification") != "OBSERVER-LQR-NO-GO"
        or r319_analysis.get("controller_result_sha256") != r319_result_digest
        or not all(r319_analysis.get("validity_guards", {}).values())
        or r319_provenance.get("controller_result", {}).get("sha256")
        != r319_result_digest
        or r319_provenance.get("analysis", {}).get("sha256")
        != r319_analysis_digest
        or r320_seal.get("round") != "R320"
        or r320_diagnostic.get("seal_sha256") != r320_seal_digest
        or r320_analysis.get("classification") != "POLE-TARGET-ELIGIBLE"
        or r320_analysis.get("diagnostic_sha256") != r320_diagnostic_digest
        or not all(r320_analysis.get("validity_guards", {}).values())
        or r320_provenance.get("diagnostic", {}).get("sha256")
        != r320_diagnostic_digest
        or r320_provenance.get("analysis", {}).get("sha256")
        != r320_analysis_digest
    ):
        raise RuntimeError("R321 parent authority contract mismatch")
    if (
        r319_result.get("output_scales") != build_contract()["output_scales"]
        or r319_result.get("action_scales") != build_contract()["action_scales"]
    ):
        raise RuntimeError("R319 sealed scale contract mismatch")
    for arm in ARMS:
        if (
            r319_analysis["arms"][arm]["examination_case_count"] != 0
            or r319_analysis["arms"][arm]["energy_ratios_to_zero"] != []
            or r319_result["cases"][arm]["examination"] != []
        ):
            raise RuntimeError("R319 hidden examination was previously accessed")
    hashes = {
        "r316_model": {"path": _path_text(R316_MODEL), "sha256": r316_model_digest},
        "r316_analysis": {
            "path": _path_text(R316_ANALYSIS),
            "sha256": r316_analysis_digest,
        },
        "r319_seal": {"path": _path_text(R319_SEAL), "sha256": r319_seal_digest},
        "r319_result": {
            "path": _path_text(R319_RESULT),
            "sha256": r319_result_digest,
        },
        "r319_analysis": {
            "path": _path_text(R319_ANALYSIS),
            "sha256": r319_analysis_digest,
        },
        "r319_provenance": {
            "path": _path_text(R319_PROVENANCE),
            "sha256": r319_provenance_digest,
        },
        "r320_seal": {"path": _path_text(R320_SEAL), "sha256": r320_seal_digest},
        "r320_diagnostic": {
            "path": _path_text(R320_DIAGNOSTIC),
            "sha256": r320_diagnostic_digest,
        },
        "r320_analysis": {
            "path": _path_text(R320_ANALYSIS),
            "sha256": r320_analysis_digest,
        },
        "r320_provenance": {
            "path": _path_text(R320_PROVENANCE),
            "sha256": r320_provenance_digest,
        },
    }
    return r316_model, hashes


def prepare(seal_path: Path) -> str:
    _model, parents = _load_parents()
    contract = build_contract()
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": _payload_sha256(contract),
        "parent": parents,
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
        raise RuntimeError("R321 seal contract drift")
    _model, parents = _load_parents()
    if seal.get("parent") != parents:
        raise RuntimeError("R321 sealed parent drift")
    for name, entry in seal["sources"].items():
        if _sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"R321 sealed source drift for {name}")
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


def _synthesize_arm(
    models: dict[str, StateSpaceRealization],
) -> tuple[dict[str, FixedPoleTargetDesign], dict[str, str], int]:
    contract = build_contract()
    designs: dict[str, FixedPoleTargetDesign] = {}
    errors: dict[str, str] = {}
    attempts = 0
    for point, realization in models.items():
        attempts += 1
        try:
            designs[point] = synthesize_fixed_pole_target(
                realization,
                output_scales=contract["output_scales"][point],
                action_scales=contract["action_scales"],
                controller_target_poles=contract["controller_target_poles"],
                observer_target_poles=contract["observer_target_poles"],
                method=contract["placement_method"],
                relative_tolerance=contract["placement_relative_tolerance"],
                maximum_iterations=contract["placement_maximum_iterations"],
            )
        except (np.linalg.LinAlgError, ValueError) as exc:
            errors[point] = type(exc).__name__
    return designs, errors, attempts


def _design_summary(result: FixedPoleTargetDesign) -> dict[str, object]:
    design = result.design
    return {
        "controller_pole_radius": design.controller_pole_radius,
        "observer_pole_radius": design.observer_pole_radius,
        "controller_target_max_abs_error": result.controller_target_max_abs_error,
        "observer_target_max_abs_error": result.observer_target_max_abs_error,
        "controller_gain_frobenius_norm": result.controller_gain_frobenius_norm,
        "observer_gain_frobenius_norm": result.observer_gain_frobenius_norm,
        "controller_iterations": result.controller_iterations,
        "observer_iterations": result.observer_iterations,
        "controller_reported_tolerance": result.controller_reported_tolerance,
        "observer_reported_tolerance": result.observer_reported_tolerance,
        "controller_warnings": list(result.controller_warnings),
        "observer_warnings": list(result.observer_warnings),
        "feedback_gain": design.feedback_gain.tolist(),
        "filter_gain": design.filter_gain.tolist(),
        "output_scales": design.output_scales.tolist(),
        "action_scales": design.action_scales.tolist(),
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
    arms: dict[str, dict[str, object]] = {}
    rows: dict[str, dict[str, list[dict[str, object]]]] = {}
    arm_designs: dict[str, dict[str, ObserverLqrDesign]] = {}
    placement_attempt_count = 0
    for name, models in arm_models.items():
        placements, errors, attempts = _synthesize_arm(models)
        placement_attempt_count += attempts
        if errors or set(placements) != set(POINT_SOC):
            arms[name] = {
                "synthesis_feasible": False,
                "synthesis_errors": errors,
                "point_designs": {},
                "development": _not_run_summary("synthesis-failed"),
                "examination": _not_run_summary("development-gate-failed"),
            }
            rows[name] = {"development": [], "examination": []}
            continue
        designs = {point: value.design for point, value in placements.items()}
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
                point: _design_summary(value) for point, value in placements.items()
            },
            "development": development,
        }
        rows[name] = {"development": development_rows, "examination": []}

    development_pass = all(
        name in arm_designs
        and all(
            arms[name]["point_designs"][point][  # type: ignore[index]
                "controller_target_max_abs_error"
            ]
            <= contract["placement_target_tolerance"]
            and arms[name]["point_designs"][point][  # type: ignore[index]
                "observer_target_max_abs_error"
            ]
            <= contract["placement_target_tolerance"]
            and designs.controller_pole_radius
            <= contract["controller_target_radius"]
            + contract["placement_target_tolerance"]
            and designs.observer_pole_radius
            <= contract["observer_target_radius"]
            + contract["placement_target_tolerance"]
            for point, designs in arm_designs[name].items()
        )
        and arms[name]["development"]["finite"] is True  # type: ignore[index]
        and arms[name]["development"]["constraint_violation_count"] == 0  # type: ignore[index]
        for name in ARMS
    )
    for name in ARMS:
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
        "output_scales": contract["output_scales"],
        "action_scales": contract["action_scales"],
        "placement_attempt_count": placement_attempt_count,
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
    model, _parents = _load_parents()
    first = _calculate(model)
    second = _calculate(model)
    deterministic = _payload_sha256(first) == _payload_sha256(second)
    examination_was_run = all(
        arm["examination"]["case_count"] == 80 for arm in first["arms"].values()
    )
    expected_examination = bool(first["development_gate_passed"])
    _retained, markov = _models(model)
    first.update(
        {
            "schema_version": 1,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "contract_payload_sha256": seal["contract_payload_sha256"],
            "validity_guards": {
                "sealed_source_identity": True,
                "parent_authority": True,
                "matrix_contract": True,
                "sealed_scale_contract": bool(
                    first["output_scales"] == seal["contract"]["output_scales"]
                    and first["action_scales"] == seal["contract"]["action_scales"]
                ),
                "fixed_template_contract": bool(
                    first["placement_attempt_count"] == 4
                    and seal["contract"]["placement_call_count_per_point_and_arm"]
                    == 1
                    and seal["contract"]["tuning_candidate_count"] == 0
                ),
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
                    for tensor in markov.values()
                ),
                "conditional_examination_contract": bool(
                    examination_was_run == expected_examination
                ),
                "eval_not_run": bool(
                    first["eval_status"] == "NOT-APPLICABLE-MODEL-ONLY"
                ),
                "no_physical_execution": bool(
                    first["physical_execution_performed"] is False
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
        or result.get("contract_payload_sha256")
        != seal["contract_payload_sha256"]
    ):
        raise RuntimeError("R321 result provenance mismatch")
    analysis = evaluate_pole_target_examination(result)
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
