#!/usr/bin/env python3
"""Seal, fit, execute, EVAL-audit, and analyse the R315 dynamic reduction."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
for path in (ROOT, SRC, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from run_r310_model_first_stage1 import (  # noqa: E402
    DYNAMIC_TOLERANCE,
    LOCAL_VECTOR_ARCHITECTURE,
    TOTAL_STEPS,
    _jsonable,
    _path_text,
    _payload_sha256,
    _read_verified_json,
    _runtime_record,
    _sha256_file,
    _write_new_json,
)
from run_r313_model_first_predictor import (  # noqa: E402
    EXPECTED_EVAL_GUARDS,
    _point,
)

from andes_rl_kundur.env.andes.model_first_contract import (  # noqa: E402
    ModelFirstConfig,
    Stage1OperatingPoint,
    stage1_power_coordinates,
)
from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (  # noqa: E402
    enforce_spectral_radius,
    fit_era_realization,
    realization_from_dict,
    realization_to_dict,
    recover_markov_parameters,
)
from andes_rl_kundur.evaluation.model_first_stage1_eval_guards import (  # noqa: E402
    build_guarded_fresh_stage1_eval_view,
)
from probes.r315_dynamic_reduction_validation import (  # noqa: E402
    evaluate_dynamic_reduction_validation,
)

ROUND_ID = "R315"
QUESTION_ID = "Q-0071"
DEFAULT_SEAL = ROOT / "memory/rounds/R315/dynamic_reduction_seal.json"
DEFAULT_OUT = ROOT / "results/r315_dynamic_reduction"
R314_OUT = ROOT / "results/r314_local_predictor"
EVAL_BOOTSTRAP_RESAMPLES = 10_000
EVAL_BOOTSTRAP_SEED = 2026080315
INPUT_WINDOW_STEPS = 5


def _holdout_operating_points() -> list[dict[str, object]]:
    return [
        {
            "name": "HR0",
            "vsg_m_device": 182.5,
            "vsg_d_device": 91.25,
            "tie_rx_scale": 1.10,
            "initial_soc": 0.43,
            "training_weights": {
                "OP0": 0.35,
                "OP1": 0.15,
                "OP2": 0.0,
                "HP1": 0.50,
            },
            "simplex": ["OP0", "OP1", "HP1"],
        },
        {
            "name": "HR1",
            "vsg_m_device": 197.5,
            "vsg_d_device": 98.75,
            "tie_rx_scale": 1.25,
            "initial_soc": 0.49,
            "training_weights": {
                "OP0": 0.35,
                "OP1": 0.0,
                "OP2": 0.15,
                "HP1": 0.50,
            },
            "simplex": ["OP0", "OP2", "HP1"],
        },
    ]


def _excitation_shapes() -> dict[str, list[float]]:
    return {
        "impulse": [0.05],
        "triangle": [0.02, 0.04, 0.05, 0.04, 0.02],
        "bipolar": [0.05, 0.05, 0.0, -0.05, -0.05],
    }


def build_contract() -> dict[str, Any]:
    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "sealed-low-order-dynamic-reduction-holdout",
        "development_authority": {
            "training_rounds": ["R312", "R313"],
            "training_questions": ["Q-0068", "Q-0069"],
            "training_trace_count": 44,
            "carrier_round": "R314",
            "carrier_holdout_accessed": False,
            "R313_HP0_fitting_forbidden": True,
            "R314_holdout_fitting_forbidden": True,
        },
        "markov_recovery": {
            "source": "five-step-rectangular-central-difference-templates",
            "pulse_width_steps": 5,
            "pulse_amplitude_system_pu": 0.05,
            "smoothing": "none",
            "late_horizon_truncation": "none",
        },
        "realization": {
            "kind": "era",
            "order": 10,
            "block_rows": 8,
            "block_columns": 8,
            "markov_horizon_steps": 25,
            "sample_period_seconds": 0.2,
            "state_initialization": "zero",
            "maximum_spectral_radius": 0.995,
            "pole_projection": "clip-magnitude-only-before-holdout",
        },
        "holdout_operating_points": _holdout_operating_points(),
        "excitation_shapes": _excitation_shapes(),
        "input_window_steps": INPUT_WINDOW_STEPS,
        "horizon_steps": TOTAL_STEPS,
        "holdout_trace_count": 50,
        "thresholds": {
            "parent_physical_total_nrmse_max": 0.15,
            "reduced_parent_total_nrmse_max": 0.10,
            "reduced_physical_total_nrmse_max": 0.15,
            "maximum_normalized_absolute_residual_max": 0.20,
            "peak_magnitude_relative_error_max": 0.10,
            "peak_timing_error_seconds_max": 0.2,
            "aggregate_cross_squared_error_reduction_min": 0.20,
            "cross_record_win_fraction_min": 0.75,
            "maximum_spectral_radius": 0.995,
        },
        "comparison_identifiability": {
            "reduced_full_vs_block": "ALLOW",
            "parent_fir_vs_reduced_era": "ALLOW-REDUCTION-FIDELITY-ONLY",
            "R314_vs_R315": "QUALIFY",
            "single_factor": (
                "retain-versus-zero-common-differential-cross-output"
            ),
            "estimand": "heldout-cross-output-prediction-error-in-frozen-reduction",
            "stay_out": [
                "predictor-class-superiority",
                "controller-efficacy",
                "distributed-execution-value",
                "multi-agent-or-MARL-value",
                "topology-generalization",
                "stability-guarantee",
                "deployment",
            ],
        },
        "eval": {
            "trigger": {
                "run_manifest_trace_count": 50,
                "verified_edge_record_count": 36,
                "source_sidecars_required": True,
            },
            "guard_synthesis": {
                "source": "authoritative R315 physical record fields",
                "mapping": EXPECTED_EVAL_GUARDS,
                "fail_closed": True,
            },
            "source_bound_view": True,
            "execution_profile": "vector_power",
            "required_active_window_seconds": 1.0,
            "bootstrap_resamples": EVAL_BOOTSTRAP_RESAMPLES,
            "bootstrap_seed": EVAL_BOOTSTRAP_SEED,
            "evidence_status": "EXTERNAL_AUTHORITY_REQUIRED",
            "effect_optimization_authorized": False,
        },
        "classification": [
            "INVALID-DYNAMIC-REDUCTION-VALIDATION",
            "DYNAMIC-REDUCTION-NO-GO",
            "DYNAMIC-REDUCTION-PASS",
        ],
        "optimization_rules": {
            "INVALID-DYNAMIC-REDUCTION-VALIDATION": "new-cause-specific-canary-only",
            "DYNAMIC-REDUCTION-NO-GO": "registered-failure-mode-branch-only",
            "DYNAMIC-REDUCTION-PASS": (
                "separate-deterministic-controller-question-may-be-opened"
            ),
        },
        "fresh_holdout_required": True,
        "holdout_fitting_forbidden": True,
        "controller_development_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R315/plan.md",
        "question": ROOT / "memory/questions/Q-0071.md",
        "adapter": Path(__file__).resolve(),
        "execution_core": ROOT / "scripts/run_r310_model_first_stage1.py",
        "lifecycle_core": ROOT / "scripts/run_r314_local_predictor.py",
        "model_contract": SRC
        / "andes_rl_kundur/env/andes/model_first_contract.py",
        "environment": SRC / "andes_rl_kundur/env/andes/model_first_env.py",
        "dynamic_reduction": SRC
        / "andes_rl_kundur/evaluation/model_first_dynamic_reduction.py",
        "validation_probe": ROOT
        / "probes/r315_dynamic_reduction_validation.py",
        "eval_view": SRC
        / "andes_rl_kundur/evaluation/model_first_stage1_eval_view.py",
        "eval_guards": SRC
        / "andes_rl_kundur/evaluation/model_first_stage1_eval_guards.py",
        "eval_v2": SRC / "andes_rl_kundur/evaluation/eval_v2.py",
        "dynamic_tests": ROOT / "tests/test_model_first_dynamic_reduction.py",
        "validation_tests": ROOT
        / "tests/test_r315_dynamic_reduction_validation.py",
        "adapter_tests": ROOT / "tests/test_r315_dynamic_reduction.py",
    }


def _sources() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _path_text(path), "sha256": _sha256_file(path)}
        for name, path in _source_paths().items()
    }


def _load_r314_development() -> tuple[dict[str, Any], dict[str, dict[str, str]]]:
    paths = {
        "predictor_model": R314_OUT / "predictor_model.json",
        "run_manifest": R314_OUT / "run_manifest.json",
        "analysis": R314_OUT / "analysis.json",
        "provenance": R314_OUT / "provenance.json",
    }
    loaded = {name: _read_verified_json(path) for name, path in paths.items()}
    predictor_artifact, predictor_digest = loaded["predictor_model"]
    run_manifest, run_digest = loaded["run_manifest"]
    analysis, analysis_digest = loaded["analysis"]
    provenance, provenance_digest = loaded["provenance"]
    predictor = predictor_artifact.get("predictor")
    if (
        predictor_artifact.get("round") != "R314"
        or predictor_artifact.get("question") != "Q-0070"
        or predictor_artifact.get("R314_holdout_accessed") is not False
        or predictor_artifact.get("R313_HP0_accessed") is not False
        or predictor_artifact.get("controller_development_authorized") is not False
        or predictor_artifact.get("training_authorized") is not False
        or not isinstance(predictor, Mapping)
        or predictor.get("training_rounds") != ["R312", "R313"]
        or predictor.get("training_questions") != ["Q-0068", "Q-0069"]
        or predictor.get("training_trace_count") != 44
        or run_manifest.get("predictor_model_sha256") != predictor_digest
        or analysis.get("classification") != "LOCAL-PREDICTOR-PASS"
        or analysis.get("predictor_model_sha256") != predictor_digest
        or analysis.get("run_manifest_sha256") != run_digest
        or analysis.get("R314_holdout_used_for_fitting") is not False
        or analysis.get("eval_integrity") is not True
        or not all(analysis.get("execution_guards", {}).values())
        or provenance.get("predictor_model", {}).get("sha256")
        != predictor_digest
        or provenance.get("run_manifest", {}).get("sha256") != run_digest
        or provenance.get("analysis", {}).get("sha256") != analysis_digest
        or provenance.get("R314_holdout_used_for_fitting") is not False
        or provenance.get("controller_development_authorized") is not False
        or provenance.get("training_authorized") is not False
    ):
        raise RuntimeError("R314 development authority chain is not valid")
    artifacts = {
        name: {"path": _path_text(paths[name]), "sha256": digest}
        for name, (_payload, digest) in loaded.items()
    }
    artifacts["provenance"]["sha256"] = provenance_digest
    return predictor_artifact, artifacts


def prepare(seal_path: Path) -> str:
    _predictor, development_artifacts = _load_r314_development()
    contract = build_contract()
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": _payload_sha256(contract),
        "development_artifacts": development_artifacts,
        "sources": _sources(),
    }
    digest = _write_new_json(seal_path, seal)
    print(f"seal_sha256={digest}", flush=True)
    return digest


def _load_seal(path: Path, expected: str) -> tuple[dict[str, Any], str]:
    seal, digest = _read_verified_json(path, expected)
    if seal.get("round") != ROUND_ID or seal.get("question") != QUESTION_ID:
        raise RuntimeError("R315 seal identity mismatch")
    if seal.get("contract_payload_sha256") != _payload_sha256(seal["contract"]):
        raise RuntimeError("R315 seal contract payload drift")
    if seal.get("contract") != build_contract():
        raise RuntimeError("R315 in-code contract drift")
    _predictor, development_artifacts = _load_r314_development()
    if seal.get("development_artifacts") != development_artifacts:
        raise RuntimeError("sealed R315 development artifact drift")
    for name, entry in seal["sources"].items():
        if _sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"sealed R315 source drift for {name}")
    return seal, digest


def _interpolated_markov_tensor(
    predictor: Mapping[str, object],
    *,
    weights: Mapping[str, object],
) -> np.ndarray:
    templates = predictor.get("templates")
    if not isinstance(templates, Mapping) or set(weights) != set(templates):
        raise ValueError("predictor templates and interpolation weights disagree")
    weight_values = np.asarray([float(weights[name]) for name in templates])
    if (
        not np.all(np.isfinite(weight_values))
        or np.any(weight_values < 0.0)
        or not np.isclose(np.sum(weight_values), 1.0, rtol=0.0, atol=1e-12)
    ):
        raise ValueError("interpolation weights must be a finite convex vector")
    coordinates = tuple(stage1_power_coordinates())
    tensor = np.zeros((TOTAL_STEPS, 4, len(coordinates)))
    for input_index, coordinate in enumerate(coordinates):
        pulse_response = np.zeros((TOTAL_STEPS, 4))
        for point_name, point_entry in templates.items():
            if not isinstance(point_entry, Mapping):
                raise ValueError("predictor point template is invalid")
            responses = point_entry.get("responses")
            if not isinstance(responses, Mapping):
                raise ValueError("predictor response map is invalid")
            pulse_response += float(weights[point_name]) * np.asarray(
                responses[coordinate], dtype=float
            )
        tensor[:, :, input_index] = recover_markov_parameters(
            pulse_response,
            pulse_width_steps=5,
            pulse_amplitude=0.05,
        )
    return tensor


def _fit_dynamic_model(
    predictor_artifact: Mapping[str, object], contract: Mapping[str, object]
) -> dict[str, object]:
    predictor = predictor_artifact["predictor"]
    if not isinstance(predictor, Mapping):
        raise ValueError("R314 predictor artifact is invalid")
    realization_contract = contract["realization"]
    if not isinstance(realization_contract, Mapping):
        raise ValueError("realization contract is invalid")
    points: dict[str, object] = {}
    for entry in contract["holdout_operating_points"]:
        if not isinstance(entry, Mapping):
            raise ValueError("holdout operating point is invalid")
        weights = entry["training_weights"]
        if not isinstance(weights, Mapping):
            raise ValueError("holdout weights are invalid")
        markov = _interpolated_markov_tensor(predictor, weights=weights)
        raw = fit_era_realization(
            markov,
            order=int(realization_contract["order"]),
            block_rows=int(realization_contract["block_rows"]),
            block_columns=int(realization_contract["block_columns"]),
        )
        maximum_radius = float(realization_contract["maximum_spectral_radius"])
        projected = raw.spectral_radius > maximum_radius
        frozen = enforce_spectral_radius(raw, maximum_radius=maximum_radius)
        points[str(entry["name"])] = {
            "training_weights": dict(weights),
            "markov_parameters": markov.tolist(),
            "raw_spectral_radius": raw.spectral_radius,
            "pole_projection_applied": projected,
            "realization": realization_to_dict(frozen),
        }
    return points


def fit(seal_path: Path, expected: str, out_dir: Path) -> None:
    seal, seal_digest = _load_seal(seal_path, expected)
    predictor_artifact, development_artifacts = _load_r314_development()
    points = _fit_dynamic_model(predictor_artifact, seal["contract"])
    artifact = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "contract_payload_sha256": seal["contract_payload_sha256"],
        "development_artifacts": development_artifacts,
        "realization_contract": seal["contract"]["realization"],
        "points": points,
        "R313_HP0_used_for_fitting": False,
        "R314_holdout_used_for_fitting": False,
        "R315_holdout_accessed": False,
        "controller_development_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }
    digest = _write_new_json(out_dir / "dynamic_model.json", artifact)
    print(f"dynamic_model_sha256={digest}", flush=True)


def _load_model(
    out_dir: Path,
    *,
    seal: Mapping[str, object],
    seal_digest: str,
    expected_sha256: str | None = None,
) -> tuple[dict[str, Any], str]:
    artifact, digest = _read_verified_json(
        out_dir / "dynamic_model.json", expected_sha256
    )
    predictor_artifact, development_artifacts = _load_r314_development()
    expected_points = _fit_dynamic_model(predictor_artifact, seal["contract"])
    points = artifact.get("points")
    points_valid = isinstance(points, Mapping) and set(points) == set(expected_points)
    if points_valid:
        for name, expected_point in expected_points.items():
            point = points[name]
            if not isinstance(point, Mapping):
                points_valid = False
                break
            try:
                realization = realization_from_dict(point["realization"])
                expected_markov = np.asarray(
                    expected_point["markov_parameters"], dtype=float
                )
                actual_markov = np.asarray(point["markov_parameters"], dtype=float)
                points_valid = bool(
                    point.get("training_weights")
                    == expected_point["training_weights"]
                    and np.allclose(
                        actual_markov, expected_markov, rtol=1e-13, atol=1e-15
                    )
                    and realization.state_matrix.shape == (10, 10)
                    and realization.input_matrix.shape == (10, 4)
                    and realization.output_matrix.shape == (4, 10)
                    and realization.feedthrough_matrix.shape == (4, 4)
                    and realization.spectral_radius <= 0.995 + 1e-10
                )
            except (KeyError, TypeError, ValueError):
                points_valid = False
            if not points_valid:
                break
    if (
        artifact.get("round") != ROUND_ID
        or artifact.get("question") != QUESTION_ID
        or artifact.get("seal_sha256") != seal_digest
        or artifact.get("contract_payload_sha256")
        != seal["contract_payload_sha256"]
        or artifact.get("development_artifacts") != development_artifacts
        or artifact.get("realization_contract") != seal["contract"]["realization"]
        or artifact.get("R313_HP0_used_for_fitting") is not False
        or artifact.get("R314_holdout_used_for_fitting") is not False
        or artifact.get("R315_holdout_accessed") is not False
        or artifact.get("controller_development_authorized") is not False
        or artifact.get("distributed_agent_implementation_authorized") is not False
        or artifact.get("training_authorized") is not False
        or not points_valid
    ):
        raise RuntimeError("R315 dynamic model provenance mismatch")
    return artifact, digest


def _signed_sequence(base: Sequence[float], sign: str) -> np.ndarray:
    if sign not in {"positive", "negative"}:
        raise ValueError("sign must be positive or negative")
    sequence = np.zeros(TOTAL_STEPS)
    values = np.asarray(base, dtype=float)
    sequence[: values.size] = values * (1.0 if sign == "positive" else -1.0)
    return sequence


def _record_path(
    out_dir: Path,
    *,
    point: str,
    shape: str,
    coordinate: str,
    sign: str,
) -> tuple[Path, str]:
    if coordinate == "zero":
        return out_dir / "records/baseline" / f"{point}__zero.json", "baseline"
    filename = f"{point}__{shape}__{coordinate}__{sign}.json"
    if coordinate == "common":
        return out_dir / "records/common" / filename, "common"
    return out_dir / "records/edge_source" / filename, "edge_source"


def _run_trace_sequence(
    *,
    point: Stage1OperatingPoint,
    coordinate: str,
    shape: str,
    sign: str,
    scalar_sequence: np.ndarray,
    seal_digest: str,
    model_digest: str,
) -> dict[str, Any]:
    from andes_rl_kundur.env.andes.model_first_env import AndesModelFirstEnv

    config = replace(
        ModelFirstConfig.for_stage1_operating_point(point),
        tds_post_initialization_convergence_tolerance=DYNAMIC_TOLERANCE,
    )
    coordinate_vectors = stage1_power_coordinates(1.0)
    requests = (
        np.zeros((TOTAL_STEPS, 4))
        if coordinate == "zero"
        else scalar_sequence[:, None]
        * np.asarray(coordinate_vectors[coordinate], dtype=float)[None, :]
    )
    env = AndesModelFirstEnv(model_first_config=config)
    rows: list[dict[str, Any]] = []
    try:
        env.reset()
        initialization_solver = _jsonable(
            env._model_first_initialization_solver_contract
        )
        initial_soc_readback = env._get_bess_soc().copy()
        zero_md = {index: np.zeros(2) for index in range(env.N_AGENTS)}
        for step, requested in enumerate(requests):
            _, _, _, info = env.step(
                zero_md, bess_power_request_pu=requested
            )
            row = _jsonable(info)
            row["step"] = step
            row["t"] = row.pop("time")
            frequency = np.asarray(row["freq_hz_physical"], dtype=float)
            row["delta_f_physical_hz"] = (frequency - 60.0).tolist()
            row["action_norm"] = [[0.0, 0.0] for _ in range(4)]
            rows.append(row)
        structural = _jsonable(env.structural_contract())
    finally:
        env.close()

    completed = len(rows) == TOTAL_STEPS and not any(
        bool(row["tds_failed"]) for row in rows
    )
    scenario = f"{point.name.lower()}_{shape}_{coordinate}"
    record: dict[str, Any] = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "seal_sha256": seal_digest,
        "dynamic_model_sha256": model_digest,
        "scenario": scenario,
        "controller": sign,
        "operating_point": point.name,
        "input_shape": shape,
        "coordinate": coordinate,
        "sign": sign,
        "location": f"{point.name}/{shape}/{coordinate}",
        "severity": f"tie_k={point.tie_rx_scale:g}",
        "initial_soc": point.initial_soc,
        "pulse_amplitude_system_pu": float(np.max(np.abs(scalar_sequence))),
        "input_sequence_system_pu": scalar_sequence.tolist(),
        "input_window_steps": INPUT_WINDOW_STEPS,
        "initial_soc_readback": initial_soc_readback.tolist(),
        "initialization_solver": initialization_solver,
        "completed": completed,
        "tds_failed": not completed,
        "n_steps": len(rows),
        "requested_steps": TOTAL_STEPS,
        "metric_frequency_basis": "andes_physical_hz",
        "andes_nominal_frequency_hz": 60.0,
        "controller_config": {
            "architecture": LOCAL_VECTOR_ARCHITECTURE,
            "area_residual": {"active_steps": INPUT_WINDOW_STEPS},
        },
        "structural": structural,
        "execution_runtime": _runtime_record(),
        "traces": rows,
    }
    if coordinate.startswith("edge_"):
        record["mechanism_trace"] = [
            {
                "total_residual_sum_system_pu": float(
                    np.sum(row["bess_requested_power_system_pu"])
                ),
                "total_residual_rms_system_pu": float(
                    np.sqrt(
                        np.mean(
                            np.square(row["bess_requested_power_system_pu"])
                        )
                    )
                ),
            }
            for row in rows
        ]
    return record


def run(seal_path: Path, expected: str, out_dir: Path) -> None:
    seal, seal_digest = _load_seal(seal_path, expected)
    model_artifact, model_digest = _load_model(
        out_dir, seal=seal, seal_digest=seal_digest
    )
    manifest_path = out_dir.resolve() / "run_manifest.json"
    if manifest_path.exists():
        raise FileExistsError(f"R315 run already exists: {manifest_path}")
    entries: list[dict[str, object]] = []
    coordinates: Sequence[str] = tuple(stage1_power_coordinates())
    shapes = seal["contract"]["excitation_shapes"]
    for point_entry in seal["contract"]["holdout_operating_points"]:
        point = _point(point_entry)
        zero_sequence = np.zeros(TOTAL_STEPS)
        zero_record = _run_trace_sequence(
            point=point,
            coordinate="zero",
            shape="zero",
            sign="zero",
            scalar_sequence=zero_sequence,
            seal_digest=seal_digest,
            model_digest=model_digest,
        )
        zero_record["training_weights"] = point_entry["training_weights"]
        zero_record["simplex"] = point_entry["simplex"]
        path, group = _record_path(
            out_dir,
            point=point.name,
            shape="zero",
            coordinate="zero",
            sign="zero",
        )
        digest = _write_new_json(path, zero_record)
        entries.append(
            {
                "path": _path_text(path),
                "sha256": digest,
                "group": group,
                "operating_point": point.name,
                "input_shape": "zero",
                "coordinate": "zero",
                "sign": "zero",
            }
        )
        print(f"trace={point.name}/zero", flush=True)
        for shape, base_sequence in shapes.items():
            for coordinate in coordinates:
                for sign in ("positive", "negative"):
                    scalar_sequence = _signed_sequence(base_sequence, sign)
                    record = _run_trace_sequence(
                        point=point,
                        coordinate=coordinate,
                        shape=shape,
                        sign=sign,
                        scalar_sequence=scalar_sequence,
                        seal_digest=seal_digest,
                        model_digest=model_digest,
                    )
                    record["training_weights"] = point_entry["training_weights"]
                    record["simplex"] = point_entry["simplex"]
                    path, group = _record_path(
                        out_dir,
                        point=point.name,
                        shape=shape,
                        coordinate=coordinate,
                        sign=sign,
                    )
                    digest = _write_new_json(path, record)
                    entries.append(
                        {
                            "path": _path_text(path),
                            "sha256": digest,
                            "group": group,
                            "operating_point": point.name,
                            "input_shape": shape,
                            "coordinate": coordinate,
                            "sign": sign,
                        }
                    )
                    print(
                        f"trace={point.name}/{shape}/{coordinate}/{sign}",
                        flush=True,
                    )
    manifest = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "dynamic_model_sha256": model_digest,
        "trace_count": len(entries),
        "records": entries,
        "fresh_holdout_execution": True,
        "validation_source_rounds_used": [],
        "development_source": model_artifact["development_artifacts"],
        "execution_runtime": _runtime_record(),
        "controller_development_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }
    digest = _write_new_json(manifest_path, manifest)
    print(f"trace_count={len(entries)}", flush=True)
    print(f"run_manifest_sha256={digest}", flush=True)


def _load_run_records(
    out_dir: Path,
    *,
    seal_digest: str,
    model_digest: str,
) -> tuple[dict[str, Any], str, list[dict[str, Any]]]:
    manifest, manifest_digest = _read_verified_json(out_dir / "run_manifest.json")
    if (
        manifest.get("round") != ROUND_ID
        or manifest.get("question") != QUESTION_ID
        or manifest.get("seal_sha256") != seal_digest
        or manifest.get("dynamic_model_sha256") != model_digest
        or manifest.get("trace_count") != 50
        or manifest.get("fresh_holdout_execution") is not True
        or manifest.get("validation_source_rounds_used") != []
        or manifest.get("controller_development_authorized") is not False
        or manifest.get("distributed_agent_implementation_authorized") is not False
        or manifest.get("training_authorized") is not False
    ):
        raise RuntimeError("R315 run manifest contract mismatch")
    records = [
        _read_verified_json(ROOT / entry["path"], entry["sha256"])[0]
        for entry in manifest.get("records", [])
    ]
    if len(records) != 50:
        raise RuntimeError("R315 manifest does not resolve to 50 records")
    return manifest, manifest_digest, records


def eval_records(seal_path: Path, expected: str, out_dir: Path) -> None:
    seal, seal_digest = _load_seal(seal_path, expected)
    _model, model_digest = _load_model(
        out_dir, seal=seal, seal_digest=seal_digest
    )
    manifest, manifest_digest, _records = _load_run_records(
        out_dir, seal_digest=seal_digest, model_digest=model_digest
    )
    edge_entries = [
        entry for entry in manifest["records"] if entry["group"] == "edge_source"
    ]
    if len(edge_entries) != 36:
        raise RuntimeError("R315 EVAL trigger requires exactly 36 edge records")
    eval_input = out_dir.resolve() / "eval_input"
    view_entries: list[dict[str, object]] = []
    for entry in edge_entries:
        record, source_digest = _read_verified_json(
            ROOT / entry["path"], entry["sha256"]
        )
        view = build_guarded_fresh_stage1_eval_view(
            record,
            source_path=entry["path"],
            source_sha256=source_digest,
            expected_round=ROUND_ID,
            expected_question=QUESTION_ID,
        )
        destination = eval_input / Path(entry["path"]).name
        view_digest = _write_new_json(destination, view)
        view_entries.append(
            {
                "path": _path_text(destination),
                "sha256": view_digest,
                "source_path": entry["path"],
                "source_sha256": source_digest,
                "guards": EXPECTED_EVAL_GUARDS,
            }
        )
    input_manifest = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "dynamic_model_sha256": model_digest,
        "run_manifest_sha256": manifest_digest,
        "record_count": len(view_entries),
        "records": view_entries,
        "guard_synthesis": "fail-closed-from-authoritative-source-fields",
        "threshold_changes": False,
        "trace_rerun": False,
        "evidence_authority_change": False,
    }
    input_digest = _write_new_json(
        out_dir / "eval_input_manifest.json", input_manifest
    )
    from andes_rl_kundur.evaluation.eval_v2 import (
        evaluate_trace_directory,
        write_scorecard,
    )

    scorecard = evaluate_trace_directory(
        eval_input,
        baseline="positive",
        execution_profile="vector_power",
        required_active_window_seconds=1.0,
        bootstrap_resamples=EVAL_BOOTSTRAP_RESAMPLES,
        bootstrap_seed=EVAL_BOOTSTRAP_SEED,
    )
    outputs = write_scorecard(scorecard, out_dir / "eval", overwrite=False)
    print(f"eval_input_manifest_sha256={input_digest}", flush=True)
    print(f"diagnostic_pass={scorecard['validity']['diagnostic_pass']}", flush=True)
    print(f"evidence_status={scorecard['evidence_status']['status']}", flush=True)
    print(json.dumps(outputs, indent=2), flush=True)


def analyse(seal_path: Path, expected: str, out_dir: Path) -> None:
    seal, seal_digest = _load_seal(seal_path, expected)
    model_artifact, model_digest = _load_model(
        out_dir, seal=seal, seal_digest=seal_digest
    )
    manifest, manifest_digest, records = _load_run_records(
        out_dir, seal_digest=seal_digest, model_digest=model_digest
    )
    input_manifest, input_manifest_digest = _read_verified_json(
        out_dir / "eval_input_manifest.json"
    )
    if (
        input_manifest.get("record_count") != 36
        or input_manifest.get("run_manifest_sha256") != manifest_digest
        or input_manifest.get("dynamic_model_sha256") != model_digest
        or input_manifest.get("threshold_changes") is not False
        or input_manifest.get("trace_rerun") is not False
        or input_manifest.get("evidence_authority_change") is not False
    ):
        raise RuntimeError("R315 EVAL input manifest contract mismatch")
    source_entries = {
        (entry["path"], entry["sha256"])
        for entry in manifest["records"]
        if entry["group"] == "edge_source"
    }
    bound_entries: set[tuple[str, str]] = set()
    for entry in input_manifest["records"]:
        view, _ = _read_verified_json(ROOT / entry["path"], entry["sha256"])
        binding = view.get("source_record")
        if (
            not isinstance(binding, Mapping)
            or binding.get("path") != entry["source_path"]
            or binding.get("sha256") != entry["source_sha256"]
            or view.get("guards") != EXPECTED_EVAL_GUARDS
        ):
            raise RuntimeError("R315 guarded EVAL view binding mismatch")
        bound_entries.add((entry["source_path"], entry["source_sha256"]))
    if bound_entries != source_entries:
        raise RuntimeError("R315 EVAL source binding mismatch")
    scorecard_path = out_dir / "eval/scorecard.json"
    scorecard, scorecard_digest = _read_verified_json(scorecard_path)
    model_provenance_valid = bool(
        model_artifact.get("seal_sha256") == seal_digest
        and model_artifact.get("development_artifacts")
        == seal["development_artifacts"]
        and model_artifact.get("R314_holdout_used_for_fitting") is False
        and model_artifact.get("R315_holdout_accessed") is False
    )
    decision = evaluate_dynamic_reduction_validation(
        records,
        model_artifact,
        scorecard,
        seal["contract"],
        expected_seal_sha256=seal_digest,
        expected_model_sha256=model_digest,
        model_provenance_valid=model_provenance_valid,
    )
    analysis = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "dynamic_model_sha256": model_digest,
        "run_manifest_sha256": manifest_digest,
        "eval_input_manifest_sha256": input_manifest_digest,
        "eval_scorecard_sha256": scorecard_digest,
        "fresh_holdout_execution": True,
        "R313_HP0_used_for_fitting": False,
        "R314_holdout_used_for_fitting": False,
        "R315_holdout_used_for_fitting": False,
        **decision,
        "optimization_rule": seal["contract"]["optimization_rules"][
            decision["classification"]
        ],
    }
    analysis_digest = _write_new_json(out_dir / "analysis.json", analysis)
    provenance = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal": {"path": _path_text(seal_path), "sha256": seal_digest},
        "dynamic_model": {
            "path": _path_text(out_dir / "dynamic_model.json"),
            "sha256": model_digest,
        },
        "run_manifest": {
            "path": _path_text(out_dir / "run_manifest.json"),
            "sha256": manifest_digest,
        },
        "eval_input_manifest": {
            "path": _path_text(out_dir / "eval_input_manifest.json"),
            "sha256": input_manifest_digest,
        },
        "eval_scorecard": {
            "path": _path_text(scorecard_path),
            "sha256": scorecard_digest,
        },
        "analysis": {
            "path": _path_text(out_dir / "analysis.json"),
            "sha256": analysis_digest,
        },
        "development_artifacts": seal["development_artifacts"],
        "sources_verified": seal["sources"],
        "contract_payload_sha256": seal["contract_payload_sha256"],
        "validation_source_rounds_used": [],
        "R313_HP0_used_for_fitting": False,
        "R314_holdout_used_for_fitting": False,
        "R315_holdout_used_for_fitting": False,
        "controller_development_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }
    provenance_digest = _write_new_json(out_dir / "provenance.json", provenance)
    print(f"classification={decision['classification']}", flush=True)
    print(f"analysis_sha256={analysis_digest}", flush=True)
    print(f"provenance_sha256={provenance_digest}", flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    for command in ("fit", "run", "eval", "analyse"):
        subparser = commands.add_parser(command)
        subparser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
        subparser.add_argument("--expected-seal-sha256", required=True)
        subparser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        prepare(args.seal)
    elif args.command == "fit":
        fit(args.seal, args.expected_seal_sha256, args.out_dir)
    elif args.command == "run":
        run(args.seal, args.expected_seal_sha256, args.out_dir)
    elif args.command == "eval":
        eval_records(args.seal, args.expected_seal_sha256, args.out_dir)
    else:
        analyse(args.seal, args.expected_seal_sha256, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
