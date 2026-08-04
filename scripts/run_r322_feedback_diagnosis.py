#!/usr/bin/env python3
"""Run the sealed R322 development-only feedback diagnosis.

Usage:
    python scripts/run_r322_feedback_diagnosis.py prepare
    python scripts/run_r322_feedback_diagnosis.py execute --expected-sha256 <seal>
    python scripts/run_r322_feedback_diagnosis.py analyse --expected-sha256 <seal>

The adapter defines no examination bank, mismatch transform, ANDES, physical,
EVAL, distributed, reward, agent, or training command. The R321 analysis is
verified by whole-file hash only and is never parsed.
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

from andes_rl_kundur.control.model_first_feedback_diagnosis import (  # noqa: E402
    FeedbackCommandDiagnosis,
    derive_common_authority_scale,
    diagnose_observer_feedback_commands,
    scale_observer_feedback_design,
    simulate_exact_state_feedback,
)
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
    synthesize_fixed_pole_target,
)
from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (  # noqa: E402
    StateSpaceRealization,
    enforce_spectral_radius,
    fit_era_realization,
    realization_from_dict,
)
from probes.r322_feedback_diagnosis_validation import (  # noqa: E402
    evaluate_feedback_diagnosis,
    identify_mechanism,
)

ROUND_ID = "R322"
QUESTION_ID = "Q-0077"
R316_MODEL = ROOT / "results/r316_dynamic_reduction/dynamic_model.json"
R321_SEAL = ROOT / "memory/rounds/R321/pole_target_examination_seal.json"
R321_ANALYSIS = ROOT / "results/r321_pole_target_examination/analysis.json"
R321_ANALYSIS_SHA256 = "03c0f7ea7d5e530b4a947b768aaab0162d88ae3c06e8629815cb6149640e0ea6"
DEFAULT_SEAL = ROOT / "memory/rounds/R322/feedback_diagnosis_seal.json"
DEFAULT_OUT = ROOT / "results/r322_feedback_diagnosis"
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


def _verify_hash_only(path: Path, expected: str) -> str:
    """Verify one artifact without decoding or exposing its JSON fields."""

    if not path.is_file():
        raise FileNotFoundError(path)
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not sidecar.is_file():
        raise FileNotFoundError(sidecar)
    digest = _sha256_file(path)
    sidecar_digest = sidecar.read_text(encoding="ascii").split()[0]
    if digest != expected or digest != sidecar_digest:
        raise RuntimeError(f"hash-only parent mismatch for {path}")
    return digest


def build_contract() -> dict[str, Any]:
    """Return the exact prospective R322 diagnostic and repair contract."""

    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "development-only-feedback-authority-diagnosis",
        "parent_round": "R321",
        "parent_claim": "CLM-0815",
        "r321_analysis_sha256": R321_ANALYSIS_SHA256,
        "r321_analysis_access": "HASH-ONLY-NO-PARSE",
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
        "output_scales": {key: list(value) for key, value in OUTPUT_SCALES.items()},
        "action_scales": list(ACTION_SCALES),
        "development_shapes": {
            "impulse": [0.05],
            "triangle": [0.02, 0.04, 0.05, 0.04, 0.02],
        },
        "development_case_count": 32,
        "decomposition_tolerance": 1.0e-10,
        "observer_rescue_absolute_floor": 0.98,
        "observer_rescue_fraction": 0.50,
        "true_state_authority_overdrive": 2.0,
        "maximum_error_command_fraction": 0.50,
        "matched_minimum_improvement": 0.02,
        "maximum_repair_pole_radius": 0.995,
        "limits": asdict(FeedbackLimits()),
        "retained_arm": "unchanged-R316-order-10-realizations",
        "matched_baseline": {
            "single_factor": "delete-common-differential-transfer-blocks",
            "era_order": 10,
            "block_rows": 8,
            "block_columns": 8,
            "maximum_model_spectral_radius": 0.995,
            "executed_plant": "unchanged-full-retained-cross-R316-realization",
        },
        "repair": {
            "kind": "one-common-analytic-authority-scalar",
            "formula": "min(1,1/worst_raw_power_ratio,1/worst_raw_ramp_ratio)",
            "pool": "both-arms-all-development-cases",
            "changed_field": "feedback-gain-only",
            "observer_gain": "unchanged",
            "tuning_candidate_count": 0,
        },
        "comparison_identifiability": {
            "decision": "QUALIFY-DEVELOPMENT-ONLY",
            "single_factor": "retain-versus-delete-named-transfer-blocks",
            "matched": [
                "full-retained-executed-plants",
                "delayed-four-coordinate-information-and-known-point",
                "four-coordinate-action-node-governor-and-limits",
                "placement-template-and-one-common-repair-scalar",
                "development-cases-timing-and-metrics",
                "zero-search-and-zero-tuning-candidates",
            ],
        },
        "classification": [
            "INVALID-DEVELOPMENT-DIAGNOSIS",
            "MECHANISM-NOT-IDENTIFIED",
            "ACTUATOR-NORMALIZED-REPAIR-NO-GO",
            "ACTUATOR-NORMALIZED-REPAIR-ELIGIBLE",
        ],
        "fresh_holdout_access": "PROHIBITED",
        "eval": "NOT-APPLICABLE-MODEL-ONLY",
        "physical_execution_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }


def _disturbance(sequence: list[float], coordinate_index: int, sign: float) -> np.ndarray:
    values = np.zeros((HORIZON_STEPS, 4))
    values[: len(sequence), coordinate_index] = sign * np.asarray(sequence)
    return values


def development_cases() -> list[FeedbackCase]:
    cases: list[FeedbackCase] = []
    for point, initial_soc in POINT_SOC.items():
        for shape, sequence in build_contract()["development_shapes"].items():
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


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R322/plan.md",
        "question": ROOT / "memory/questions/Q-0077.md",
        "r316_model": R316_MODEL,
        "r321_seal": R321_SEAL,
        "r321_analysis_hash_only": R321_ANALYSIS,
        "observer_feedback_module": SRC
        / "andes_rl_kundur/control/model_first_observer_lqr.py",
        "pole_target_module": SRC
        / "andes_rl_kundur/control/model_first_pole_target.py",
        "diagnosis_module": SRC
        / "andes_rl_kundur/control/model_first_feedback_diagnosis.py",
        "validation_probe": ROOT / "probes/r322_feedback_diagnosis_validation.py",
        "adapter": Path(__file__).resolve(),
        "diagnosis_tests": ROOT / "tests/test_model_first_feedback_diagnosis.py",
        "validation_tests": ROOT
        / "tests/test_r322_feedback_diagnosis_validation.py",
        "adapter_tests": ROOT / "tests/test_r322_feedback_diagnosis.py",
    }


def _sources() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _path_text(path), "sha256": _sha256_file(path)}
        for name, path in _source_paths().items()
    }


def _load_parents() -> tuple[dict[str, Any], dict[str, dict[str, str]]]:
    model, model_digest = _read_verified_json(R316_MODEL)
    r321_seal, r321_seal_digest = _read_verified_json(R321_SEAL)
    analysis_digest = _verify_hash_only(R321_ANALYSIS, R321_ANALYSIS_SHA256)
    contract = r321_seal.get("contract", {})
    if (
        model.get("round") != "R316"
        or set(model.get("points", {})) != set(POINT_SOC)
        or r321_seal.get("round") != "R321"
        or r321_seal.get("question") != "Q-0076"
        or contract.get("controller_target_poles")
        != build_contract()["controller_target_poles"]
        or contract.get("observer_target_poles")
        != build_contract()["observer_target_poles"]
        or contract.get("output_scales") != build_contract()["output_scales"]
        or contract.get("action_scales") != build_contract()["action_scales"]
        or contract.get("placement_method") != build_contract()["placement_method"]
        or contract.get("placement_relative_tolerance")
        != build_contract()["placement_relative_tolerance"]
        or contract.get("placement_maximum_iterations")
        != build_contract()["placement_maximum_iterations"]
    ):
        raise RuntimeError("R322 parent or exact-design contract mismatch")
    return model, {
        "r316_model": {"path": _path_text(R316_MODEL), "sha256": model_digest},
        "r321_seal": {
            "path": _path_text(R321_SEAL),
            "sha256": r321_seal_digest,
        },
        "r321_analysis_hash_only": {
            "path": _path_text(R321_ANALYSIS),
            "sha256": analysis_digest,
            "access": "HASH-ONLY-NO-PARSE",
        },
    }


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
        raise RuntimeError("R322 seal contract drift")
    _model, parents = _load_parents()
    if seal.get("parent") != parents:
        raise RuntimeError("R322 sealed parent drift")
    for name, entry in seal["sources"].items():
        if _sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"R322 sealed source drift for {name}")
    return seal, digest


def _models(
    model: dict[str, Any],
) -> tuple[dict[str, StateSpaceRealization], dict[str, np.ndarray]]:
    retained = {
        name: realization_from_dict(model["points"][name]["realization"])
        for name in POINT_SOC
    }
    markov = {
        name: np.asarray(model["points"][name]["markov_parameters"], dtype=float)
        for name in POINT_SOC
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
        realization = fit_era_realization(
            delete_common_differential_markov_blocks(tensor),
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


def _designs(models: dict[str, StateSpaceRealization]) -> dict[str, ObserverLqrDesign]:
    contract = build_contract()
    return {
        point: synthesize_fixed_pole_target(
            realization,
            output_scales=contract["output_scales"][point],
            action_scales=contract["action_scales"],
            controller_target_poles=contract["controller_target_poles"],
            observer_target_poles=contract["observer_target_poles"],
            method=contract["placement_method"],
            relative_tolerance=contract["placement_relative_tolerance"],
            maximum_iterations=contract["placement_maximum_iterations"],
        ).design
        for point, realization in models.items()
    }


def _original_arm(
    plants: dict[str, StateSpaceRealization],
    designs: dict[str, ObserverLqrDesign],
    *,
    limits: FeedbackLimits,
) -> tuple[dict[str, object], list[dict[str, object]], list[FeedbackCommandDiagnosis]]:
    rows: list[dict[str, object]] = []
    diagnoses: list[FeedbackCommandDiagnosis] = []
    observer_ratios: list[float] = []
    exact_ratios: list[float] = []
    overdrive_ratios: list[float] = []
    error_ratios: list[float] = []
    finite = True
    violations = 0
    for case in development_cases():
        plant = plants[case.point]
        design = designs[case.point]
        zero = simulate_delayed_output_feedback(
            plant,
            case.disturbance,
            gain=np.zeros((4, 4)),
            initial_soc=case.initial_soc,
            limits=limits,
        )
        observer = simulate_observer_lqr_feedback(
            plant,
            case.disturbance,
            design=design,
            initial_soc=case.initial_soc,
            limits=limits,
        )
        diagnosis = diagnose_observer_feedback_commands(
            plant,
            case.disturbance,
            design=design,
            trace=observer,
            limits=limits,
        )
        exact = simulate_exact_state_feedback(
            plant,
            case.disturbance,
            design=design,
            initial_soc=case.initial_soc,
            limits=limits,
        )
        denominator = max(zero.output_energy, np.finfo(float).tiny)
        observer_ratio = observer.output_energy / denominator
        exact_ratio = exact.output_energy / denominator
        overdrive = max(
            diagnosis.true_state_raw_node_power_ratio,
            diagnosis.true_state_raw_node_ramp_ratio,
        )
        row = {
            "case": case.name,
            "point": case.point,
            "observer_energy_ratio_to_zero": observer_ratio,
            "exact_state_energy_ratio_to_zero": exact_ratio,
            "raw_node_power_ratio": diagnosis.raw_node_power_ratio,
            "raw_node_ramp_ratio": diagnosis.raw_node_ramp_ratio,
            "true_state_overdrive_ratio": overdrive,
            "estimation_error_command_norm_ratio": (
                diagnosis.estimation_error_command_norm_ratio
            ),
            "projection_residual_energy": float(
                np.sum(np.square(diagnosis.projection_residual_node_actions))
            ),
            "observer_governor_intervention_count": (
                observer.governor_intervention_count
            ),
            "exact_state_governor_intervention_count": (
                exact.governor_intervention_count
            ),
            "maximum_decomposition_error": diagnosis.maximum_decomposition_error,
            "maximum_output_replay_error": diagnosis.maximum_output_replay_error,
            "maximum_action_replay_error": diagnosis.maximum_action_replay_error,
            "observer_constraint_violation_count": observer.constraint_violation_count,
            "exact_state_constraint_violation_count": exact.constraint_violation_count,
        }
        row_finite = all(
            np.isfinite(value) for key, value in row.items() if key not in {"case", "point"}
        )
        finite = finite and row_finite
        violations += (
            observer.constraint_violation_count + exact.constraint_violation_count
        )
        observer_ratios.append(observer_ratio)
        exact_ratios.append(exact_ratio)
        overdrive_ratios.append(overdrive)
        error_ratios.append(diagnosis.estimation_error_command_norm_ratio)
        rows.append(row)
        diagnoses.append(diagnosis)
    return (
        {
            "case_count": len(rows),
            "finite": finite,
            "constraint_violation_count": violations,
            "observer_energy_ratios_to_zero": observer_ratios,
            "exact_state_energy_ratios_to_zero": exact_ratios,
            "true_state_overdrive_ratios": overdrive_ratios,
            "estimation_error_command_norm_ratios": error_ratios,
        },
        rows,
        diagnoses,
    )


def _repair_arm(
    plants: dict[str, StateSpaceRealization],
    designs: dict[str, ObserverLqrDesign],
    *,
    limits: FeedbackLimits,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    rows: list[dict[str, object]] = []
    ratios: list[float] = []
    finite = True
    violations = 0
    for case in development_cases():
        plant = plants[case.point]
        zero = simulate_delayed_output_feedback(
            plant,
            case.disturbance,
            gain=np.zeros((4, 4)),
            initial_soc=case.initial_soc,
            limits=limits,
        )
        trace = simulate_observer_lqr_feedback(
            plant,
            case.disturbance,
            design=designs[case.point],
            initial_soc=case.initial_soc,
            limits=limits,
        )
        denominator = max(zero.output_energy, np.finfo(float).tiny)
        ratio = trace.output_energy / denominator
        row = {
            "case": case.name,
            "point": case.point,
            "energy_ratio_to_zero": ratio,
            "governor_intervention_count": trace.governor_intervention_count,
            "constraint_violation_count": trace.constraint_violation_count,
        }
        finite = finite and all(
            np.isfinite(value) for key, value in row.items() if key not in {"case", "point"}
        )
        violations += trace.constraint_violation_count
        ratios.append(ratio)
        rows.append(row)
    return (
        {
            "case_count": len(rows),
            "finite": finite,
            "constraint_violation_count": violations,
            "point_designs": {
                point: {
                    "controller_pole_radius": design.controller_pole_radius,
                    "observer_pole_radius": design.observer_pole_radius,
                }
                for point, design in designs.items()
            },
            "energy_ratios_to_zero": ratios,
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
    arm_designs = {arm: _designs(models) for arm, models in arm_models.items()}
    originals: dict[str, dict[str, object]] = {}
    original_rows: dict[str, list[dict[str, object]]] = {}
    all_diagnoses: list[FeedbackCommandDiagnosis] = []
    for arm in ARMS:
        summary, rows, diagnoses = _original_arm(
            retained, arm_designs[arm], limits=limits
        )
        originals[arm] = summary
        original_rows[arm] = rows
        all_diagnoses.extend(diagnoses)
    mechanism = identify_mechanism(originals)  # type: ignore[arg-type]
    repair_arms: dict[str, dict[str, object]] = {}
    repair_rows: dict[str, list[dict[str, object]]] = {}
    scale: float | None = None
    scale_check: float | None = None
    if mechanism != "MIXED-MECHANISM":
        scale = derive_common_authority_scale(all_diagnoses)
        scale_check = min(
            1.0,
            1.0
            / max(
                max(
                    item.raw_node_power_ratio,
                    item.raw_node_ramp_ratio,
                )
                for item in all_diagnoses
            ),
        )
        for arm in ARMS:
            scaled = {
                point: scale_observer_feedback_design(design, scale)
                for point, design in arm_designs[arm].items()
            }
            summary, rows = _repair_arm(retained, scaled, limits=limits)
            repair_arms[arm] = summary
            repair_rows[arm] = rows
    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "original_arms": originals,
        "mechanism_signature": mechanism,
        "common_authority_scale": scale,
        "common_authority_scale_check": scale_check,
        "repair_arms": repair_arms,
        "cases": {"original": original_rows, "repair": repair_rows},
        "maximum_decomposition_error": max(
            row["maximum_decomposition_error"]
            for rows in original_rows.values()
            for row in rows
        ),
        "maximum_output_replay_error": max(
            row["maximum_output_replay_error"]
            for rows in original_rows.values()
            for row in rows
        ),
        "maximum_action_replay_error": max(
            row["maximum_action_replay_error"]
            for rows in original_rows.values()
            for row in rows
        ),
        "r321_analysis_access": "HASH-ONLY-NO-PARSE",
        "r321_examination_case_accessed": False,
        "fresh_holdout_accessed": False,
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
    contract = seal["contract"]
    target_error_ok = all(
        design.controller_pole_radius <= 0.98 + contract["placement_target_tolerance"]
        and design.observer_pole_radius <= 0.94 + contract["placement_target_tolerance"]
        for designs in (
            _designs(_models(model)[0]),
            _designs(_cross_deleted_models(_models(model)[1])),
        )
        for design in designs.values()
    )
    scale_contract = bool(
        (
            first["mechanism_signature"] == "MIXED-MECHANISM"
            and first["common_authority_scale"] is None
            and first["repair_arms"] == {}
        )
        or (
            first["mechanism_signature"] != "MIXED-MECHANISM"
            and first["common_authority_scale"]
            == first["common_authority_scale_check"]
        )
    )
    first.update(
        {
            "schema_version": 1,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "contract_payload_sha256": seal["contract_payload_sha256"],
            "validity_guards": {
                "sealed_source_identity": True,
                "parent_hash_only": bool(
                    first["r321_analysis_access"] == "HASH-ONLY-NO-PARSE"
                ),
                "exact_design_contract": target_error_ok,
                "matrix_contract": True,
                "development_only_contract": bool(
                    first["r321_examination_case_accessed"] is False
                    and first["fresh_holdout_accessed"] is False
                ),
                "decomposition_identity": bool(
                    first["maximum_decomposition_error"]
                    <= contract["decomposition_tolerance"]
                    and first["maximum_output_replay_error"]
                    <= contract["decomposition_tolerance"]
                    and first["maximum_action_replay_error"]
                    <= contract["decomposition_tolerance"]
                ),
                "deterministic_replay": deterministic,
                "case_contract": bool(len(development_cases()) == 32),
                "common_scale_contract": scale_contract,
                "comparison_contract": bool(
                    contract["comparison_identifiability"]["decision"]
                    == "QUALIFY-DEVELOPMENT-ONLY"
                    and contract["repair"]["tuning_candidate_count"] == 0
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
    digest = _write_new_json(out_dir / "diagnostic_result.json", first)
    print(f"diagnostic_result_sha256={digest}", flush=True)
    return digest


def analyse(seal_path: Path, expected: str, out_dir: Path) -> str:
    seal, seal_digest = _load_seal(seal_path, expected)
    result, result_digest = _read_verified_json(out_dir / "diagnostic_result.json")
    if (
        result.get("seal_sha256") != seal_digest
        or result.get("contract_payload_sha256")
        != seal["contract_payload_sha256"]
    ):
        raise RuntimeError("R322 result provenance mismatch")
    analysis = evaluate_feedback_diagnosis(result)
    analysis.update(
        {
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "diagnostic_result_sha256": result_digest,
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
        "diagnostic_result": {
            "path": _path_text(out_dir / "diagnostic_result.json"),
            "sha256": result_digest,
        },
        "analysis": {
            "path": _path_text(out_dir / "analysis.json"),
            "sha256": analysis_digest,
        },
        "parent": seal["parent"],
        "r321_analysis_access": "HASH-ONLY-NO-PARSE",
        "r321_examination_case_accessed": False,
        "fresh_holdout_accessed": False,
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
