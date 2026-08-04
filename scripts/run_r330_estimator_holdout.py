"""Prepare, execute, and analyse the R330 untouched estimator holdout."""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple

import numpy as np
from threadpoolctl import threadpool_info, threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
for import_root in (ROOT, ROOT / "src"):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

import scripts.run_r329_disturbance_estimator as r329  # noqa: E402
from probes.r330_estimator_holdout import analyse_r330_holdout  # noqa: E402

from andes_rl_kundur.control.model_first_constrained_horizon import (  # noqa: E402
    _advance_soc,
)
from andes_rl_kundur.control.model_first_constrained_qp import (  # noqa: E402
    SparseConstrainedHorizonSolver,
)
from andes_rl_kundur.control.model_first_disturbance_estimator import (  # noqa: E402
    DisturbanceEstimatorDesign,
    advance_disturbance_estimate,
)
from andes_rl_kundur.control.model_first_offline_feedback import (  # noqa: E402
    FeedbackLimits,
)

ROUND_ID = "R330"
QUESTION_ID = "Q-0083"
R329_SEAL = ROOT / "memory/rounds/R329/disturbance_estimator_seal.json"
R329_EXECUTION = ROOT / "results/r329_disturbance_estimator/execution.json"
R329_ANALYSIS = ROOT / "results/r329_disturbance_estimator/analysis.json"
R329_PROVENANCE = ROOT / "results/r329_disturbance_estimator/provenance.json"
R329_MANIFEST = ROOT / "results/r329_disturbance_estimator/run_manifest.json"
R329_PLAN = ROOT / "memory/rounds/R329/plan.md"
R329_QUESTION = ROOT / "memory/questions/Q-0082.md"
R326_SEAL = ROOT / "memory/rounds/R326/solver_adequacy_seal.json"
R325_ADAPTER = ROOT / "scripts/run_r325_constrained_horizon.py"
DEFAULT_SEAL = ROOT / "memory/rounds/R330/estimator_holdout_seal.json"
DEFAULT_OUT = ROOT / "results/r330_estimator_holdout"
HOLDOUT_WORKERS = min(8, os.cpu_count() or 1)

_WORKER_PLANTS: dict[str, Any] | None = None
_WORKER_CONTROLLERS: dict[str, Any] | None = None
_WORKER_ESTIMATORS: dict[str, DisturbanceEstimatorDesign] | None = None
_WORKER_TRANSFORMS: dict[str, np.ndarray] | None = None
_WORKER_NATIVE_THREAD_LIMIT_VALID: bool | None = None
_THREAD_LIMITER: Any = None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path_text(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


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


def _write_new_json(path: Path, payload: object) -> str:
    return r329._write_new_json(path, payload)


def _array_record(values: object) -> dict[str, object]:
    array = np.ascontiguousarray(np.asarray(values))
    return {
        "shape": list(array.shape),
        "dtype": array.dtype.str,
        "bytes_sha256": hashlib.sha256(array.tobytes(order="C")).hexdigest(),
    }


def _point_design_fingerprint(
    plant: Any,
    controller: Any,
    estimator: DisturbanceEstimatorDesign,
) -> dict[str, object]:
    arrays = {
        "plant_state": plant.state_matrix,
        "plant_input": plant.input_matrix,
        "plant_output": plant.output_matrix,
        "plant_feedthrough": plant.feedthrough_matrix,
        "plant_singular_values": plant.retained_singular_values,
        "controller_state": controller.augmented_model.state_matrix,
        "controller_input": controller.augmented_model.input_matrix,
        "controller_measurement": controller.augmented_model.measurement_matrix,
        "controller_regulated_output": (controller.augmented_model.regulated_output_matrix),
        "controller_feedthrough": controller.augmented_model.feedthrough_matrix,
        "controller_filter_gain": controller.filter_gain,
        "controller_output_scales": controller.output_scales,
        "controller_action_scales": controller.action_scales,
        "controller_observer_poles": controller.observer_poles,
        "estimator_transition": estimator.transition_matrix,
        "estimator_control": estimator.control_matrix,
        "estimator_measurement": estimator.measurement_matrix,
        "estimator_feedthrough": estimator.feedthrough_matrix,
        "estimator_filter_gain": estimator.filter_gain,
        "estimator_covariance": estimator.covariance,
        "estimator_process_covariance": estimator.process_covariance,
        "estimator_measurement_covariance": estimator.measurement_covariance,
    }
    records = {name: _array_record(value) for name, value in arrays.items()}
    scalars = {
        "controller_horizon_steps": int(controller.horizon_steps),
        "controller_observer_target_max_abs_error": float(controller.observer_target_max_abs_error),
        "estimator_physical_state_order": int(estimator.physical_state_order),
        "estimator_observability_rank": int(estimator.observability_rank),
    }
    return {
        "payload_sha256": _payload_sha256({"arrays": records, "scalars": scalars}),
        "arrays": records,
        "scalars": scalars,
    }


def _design_fingerprints(
    plants: dict[str, Any],
    controllers: dict[str, Any],
    estimators: dict[str, DisturbanceEstimatorDesign],
) -> dict[str, dict[str, object]]:
    if (
        set(plants) != {"HS0", "HS1"}
        or set(plants) != set(controllers)
        or set(plants) != set(estimators)
    ):
        raise RuntimeError("R329 design point inventory is not exactly HS0 and HS1")
    return {
        point: _point_design_fingerprint(plants[point], controllers[point], estimators[point])
        for point in sorted(plants)
    }


def _mismatch_records() -> dict[str, dict[str, object]]:
    return {
        name: _array_record(matrix)
        for name, matrix in r329.r328.r326.r325.mismatch_transforms().items()
    }


def _case_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for case in r329.r328.r326.r325.holdout_cases():
        base = {
            "name": str(case.name),
            "point": str(case.point),
            "initial_soc": float(case.initial_soc),
            "disturbance": _array_record(case.disturbance),
        }
        records.append({**base, "payload_sha256": _payload_sha256(base)})
    return records


def _limits_record() -> dict[str, object]:
    return asdict(FeedbackLimits())


def _runtime_dependency_fingerprint() -> dict[str, object]:
    fingerprint = dict(r329.r328.r326.dependency_fingerprint())
    fingerprint["threadpoolctl_version"] = r329.r328.r326.importlib.metadata.version(
        "threadpoolctl"
    )
    fingerprint["threadpoolctl_distribution_sha256"] = r329.r328.r326._distribution_hash(
        "threadpoolctl"
    )
    return fingerprint


def _formal_designs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    return r329._formal_designs()


def build_contract() -> dict[str, object]:
    parent = r329.r328._r326_contract()
    plants, controllers, estimators = _formal_designs()
    case_records = _case_records()
    mismatch_modes = list(r329.r328.r326.r325.mismatch_transforms())
    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "model-only-frozen-estimator-untouched-holdout",
        "parent_round": "R329",
        "points": ["HS0", "HS1"],
        "holdout_case_names": [str(record["name"]) for record in case_records],
        "holdout_case_records": case_records,
        "holdout_base_case_count": len(case_records),
        "mismatch_modes": mismatch_modes,
        "holdout_case_count": len(case_records) * len(mismatch_modes),
        "solver": deepcopy(parent["solver"]),
        "limits": _limits_record(),
        "runtime_dependency_fingerprint": _runtime_dependency_fingerprint(),
        "gates": {
            "holdout_mean_output_energy_ratio_maximum": parent["gates"][
                "holdout_mean_output_energy_ratio_maximum"
            ],
            "holdout_worst_output_energy_ratio_maximum": parent["gates"][
                "holdout_worst_output_energy_ratio_maximum"
            ],
        },
        "frozen_design_fingerprints": _design_fingerprints(plants, controllers, estimators),
        "mismatch_fingerprints": _mismatch_records(),
        "holdout": {
            "candidate_count": 1,
            "resynthesis_or_tuning": "forbidden",
            "output_definition": "model-output-plus-registered-linear-mismatch",
            "zero_control_comparator": "same-plant-case-mismatch-and-score",
            "maximum_normalized_solver_residual_ratio": 1.0,
            "holdout_workers": HOLDOUT_WORKERS,
            "native_numerical_threads_per_worker": 1,
            "canonical_pass_count": 2,
            "physical_execution": "forbidden",
        },
        "comparison_identifiability": {
            "decision": "ALLOW",
            "estimand": "frozen-R329-package-versus-zero-control-on-registered-holdout",
            "claim_ceiling": "this-reduced-model-package-and-holdout-only",
        },
        "classification": [
            "INVALID-ESTIMATOR-HOLDOUT",
            "ESTIMATOR-HOLDOUT-NO-GO",
            "ESTIMATOR-HOLDOUT-PASS",
        ],
        "eval": "NOT-APPLICABLE-DETERMINISTIC-MODEL-ONLY",
        "physical_execution_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R330/plan.md",
        "question": ROOT / "memory/questions/Q-0083.md",
        "r329_seal": R329_SEAL,
        "r329_execution": R329_EXECUTION,
        "r329_analysis": R329_ANALYSIS,
        "r329_provenance": R329_PROVENANCE,
        "r329_manifest": R329_MANIFEST,
        "r329_final_plan": R329_PLAN,
        "r329_final_question": R329_QUESTION,
        "r326_seal": R326_SEAL,
        "r325_holdout_definition": R325_ADAPTER,
        "r329_claim": ROOT / "memory/claims/CLM-0855.md",
        "r329_feed": ROOT / "paper/decoupling_marl_model_first/reports/R329.md",
        "controller_module": (ROOT / "src/andes_rl_kundur/control/model_first_constrained_qp.py"),
        "controller_formulation_module": (
            ROOT / "src/andes_rl_kundur/control/model_first_constrained_horizon.py"
        ),
        "feedback_limits_module": (
            ROOT / "src/andes_rl_kundur/control/model_first_offline_feedback.py"
        ),
        "dynamic_reduction_module": (
            ROOT / "src/andes_rl_kundur/evaluation/model_first_dynamic_reduction.py"
        ),
        "action_map_module": ROOT / "src/andes_rl_kundur/env/andes/model_first_contract.py",
        "estimator_module": (
            ROOT / "src/andes_rl_kundur/control/model_first_disturbance_estimator.py"
        ),
        "validation_probe": ROOT / "probes/r330_estimator_holdout.py",
        "adapter": ROOT / "scripts/run_r330_estimator_holdout.py",
        "validation_tests": ROOT / "tests/test_r330_estimator_holdout.py",
        "adapter_tests": ROOT / "tests/test_r330_estimator_holdout_adapter.py",
        "project_dependencies": ROOT / "pyproject.toml",
        "artifact_io": ROOT / "memory/tools/artifact_io.py",
    }


def _sources() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _path_text(path), "sha256": _sha256_file(path)}
        for name, path in _source_paths().items()
    }


def _parent_bundle() -> dict[str, object]:
    r329_seal, seal_digest = r329.r328.r326.r325._read_verified_json(
        R329_SEAL,
        "a36340c17ca5738946d2bc42f7ddb54a17af1a3211d98f58bec0c7fcebd405aa",
    )
    execution, execution_digest = r329.r328.r326.r325._read_verified_json(
        R329_EXECUTION,
        "7c00deed23592096f9e1b9c10563f9a29f76ef985b74e7d273b82276c824da27",
    )
    analysis, analysis_digest = r329.r328.r326.r325._read_verified_json(
        R329_ANALYSIS,
        "5c2a7bc9cbde1595bee2def418a13c13a60cb378d1db12b0baeb4f8ca539ca74",
    )
    provenance, provenance_digest = r329.r328.r326.r325._read_verified_json(
        R329_PROVENANCE,
        "c8132996e3d2236deb41d4b168ac7beba0d82ec9e57d7793d35f41d20353181f",
    )
    manifest, manifest_digest = r329.r328.r326.r325._read_verified_json(
        R329_MANIFEST,
        "7755eaf801747126ec36dffdbf4523927303738c3717a53b3f70dd7883f214a5",
    )
    r328_source = r329_seal["sources"].get("r328_seal", {})
    if r328_source.get("path") != "memory/rounds/R328/estimation_cause_seal.json":
        raise RuntimeError("R329 does not bind the expected R328 seal path")
    r328_seal, r328_seal_digest = r329.r328.r326.r325._read_verified_json(
        ROOT / r328_source["path"], r328_source.get("sha256")
    )
    r326_source = r328_seal["sources"].get("r326_seal", {})
    if r326_source.get("path") != _path_text(R326_SEAL):
        raise RuntimeError("R328 does not bind the expected R326 seal path")
    r326_seal, r326_seal_digest = r329.r328.r326.r325._read_verified_json(
        R326_SEAL, r326_source.get("sha256")
    )
    r326_contract = r329.r328._r326_contract()
    drifted_r329_sources = {
        name
        for name, record in r329_seal["sources"].items()
        if _sha256_file(ROOT / record["path"]) != record["sha256"]
    }
    if (
        r329_seal.get("round") != "R329"
        or r329_seal.get("question") != "Q-0082"
        or r329_seal.get("contract_payload_sha256") != _payload_sha256(r329_seal.get("contract"))
        or drifted_r329_sources != {"plan", "question"}
        or analysis.get("classification") != "AUGMENTED-ESTIMATOR-DEVELOPMENT-PASS"
        or analysis.get("holdout_accessed") is not False
        or execution.get("holdout_accessed") is not False
        or execution.get("deterministic_execution_replay") is not True
        or execution.get("seal_sha256") != seal_digest
        or execution.get("contract_payload_sha256") != r329_seal["contract_payload_sha256"]
        or analysis.get("seal_sha256") != seal_digest
        or analysis.get("execution_sha256") != execution_digest
        or provenance.get("seal_sha256") != seal_digest
        or provenance.get("execution_sha256") != execution_digest
        or provenance.get("analysis_sha256") != analysis_digest
        or manifest.get("classification") != "AUGMENTED-ESTIMATOR-DEVELOPMENT-PASS"
        or manifest.get("files")
        != {
            "execution.json": execution_digest,
            "analysis.json": analysis_digest,
            "provenance.json": provenance_digest,
        }
        or r326_seal.get("contract") != r326_contract
        or r326_seal.get("contract_payload_sha256") != _payload_sha256(r326_contract)
    ):
        raise RuntimeError("R329 does not authorize the untouched holdout")
    return {
        "r329_seal": {"path": _path_text(R329_SEAL), "sha256": seal_digest},
        "r329_execution": {
            "path": _path_text(R329_EXECUTION),
            "sha256": execution_digest,
        },
        "r329_analysis": {
            "path": _path_text(R329_ANALYSIS),
            "sha256": analysis_digest,
        },
        "r329_provenance": {
            "path": _path_text(R329_PROVENANCE),
            "sha256": provenance_digest,
        },
        "r329_manifest": {
            "path": _path_text(R329_MANIFEST),
            "sha256": manifest_digest,
        },
        "r329_contract_payload_sha256": r329_seal["contract_payload_sha256"],
        "r329_expected_closure_source_drift": ["plan", "question"],
        "r326_seal": {"path": _path_text(R326_SEAL), "sha256": r326_seal_digest},
        "r326_authority": {
            "r328_seal_sha256": r328_seal_digest,
            "r328_source_path": r328_source["path"],
            "r326_source_sha256": r326_source["sha256"],
        },
        "r326_contract_payload_sha256": r326_seal["contract_payload_sha256"],
    }


def prepare(seal_path: Path) -> str:
    parent = _parent_bundle()
    contract = build_contract()
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": _payload_sha256(contract),
        "parent": parent,
        "sources": _sources(),
    }
    return _write_new_json(seal_path, seal)


def _load_seal(path: Path, expected: str) -> tuple[dict[str, Any], str]:
    seal, digest = r329.r328.r326.r325._read_verified_json(path, expected)
    parent = _parent_bundle()
    contract = build_contract()
    if (
        seal.get("round") != ROUND_ID
        or seal.get("question") != QUESTION_ID
        or seal.get("contract") != contract
        or seal.get("contract_payload_sha256") != _payload_sha256(contract)
        or seal.get("parent") != parent
        or seal.get("sources") != _sources()
    ):
        raise RuntimeError("R330 seal contract, parent, or source drift")
    return seal, digest


class HoldoutTask(NamedTuple):
    index: int
    case: Any
    mismatch_name: str
    phase: str


def _initialize_worker(
    plants: dict[str, Any],
    controllers: dict[str, Any],
    estimators: dict[str, DisturbanceEstimatorDesign],
    transforms: dict[str, np.ndarray],
) -> None:
    global _WORKER_PLANTS, _WORKER_CONTROLLERS, _WORKER_ESTIMATORS
    global _WORKER_TRANSFORMS, _WORKER_NATIVE_THREAD_LIMIT_VALID, _THREAD_LIMITER
    _THREAD_LIMITER = threadpool_limits(limits=1)
    _WORKER_NATIVE_THREAD_LIMIT_VALID = all(
        isinstance(record.get("num_threads"), int)
        and not isinstance(record.get("num_threads"), bool)
        and int(record["num_threads"]) <= 1
        for record in threadpool_info()
    )
    _WORKER_PLANTS = plants
    _WORKER_CONTROLLERS = controllers
    _WORKER_ESTIMATORS = estimators
    _WORKER_TRANSFORMS = transforms


def _simulate_holdout_row(
    plant: Any,
    controller: Any,
    estimator: DisturbanceEstimatorDesign,
    case: Any,
    mismatch_name: str,
    mismatch: np.ndarray,
    phase: str,
    native_thread_limit_valid: bool,
) -> dict[str, object]:
    limits = FeedbackLimits()
    state_matrix = np.asarray(plant.state_matrix, dtype=float)
    input_matrix = np.asarray(plant.input_matrix, dtype=float)
    output_matrix = np.asarray(plant.output_matrix, dtype=float)
    feedthrough = np.asarray(plant.feedthrough_matrix, dtype=float)
    disturbances = np.asarray(case.disturbance, dtype=float)
    state = np.zeros(state_matrix.shape[0])
    latent_prior = np.zeros(estimator.transition_matrix.shape[0])
    previous_output = np.zeros(4)
    previous_coordinate_action = np.zeros(4)
    previous_node_action = np.zeros(4)
    current_soc = np.full(4, float(case.initial_soc))
    solver = SparseConstrainedHorizonSolver(controller, limits)
    solver.reset()
    outputs = np.zeros_like(disturbances)
    node_actions = np.zeros_like(disturbances)
    coordinate_actions = np.zeros_like(disturbances)
    soc_history = np.zeros((disturbances.shape[0] + 1, 4))
    soc_history[0] = current_soc
    maximum_residual = 0.0
    maximum_primal_ratio = 0.0
    maximum_dual_ratio = 0.0
    maximum_iterations = 0
    base_row: dict[str, object] = {
        "arm": "retained_cross",
        "phase": phase,
        "case": case.name,
        "mismatch": mismatch_name,
        "native_thread_limit_valid": native_thread_limit_valid,
    }
    try:
        zero_energy = r329.r328.r326.r325._zero_energy(plant, case, mismatch)
        if zero_energy <= np.finfo(float).tiny:
            raise RuntimeError("zero-control output energy is degenerate")
        for step, disturbance in enumerate(disturbances):
            if step:
                estimate_step = advance_disturbance_estimate(
                    estimator,
                    prior_estimate=latent_prior,
                    previous_delivered_output=previous_output,
                    previous_executed_action=previous_coordinate_action,
                )
                latent_prior = estimate_step.predicted_estimate
            controller_estimate = np.concatenate((latent_prior[: state.size], previous_output))
            result = solver.solve(
                corrected_estimate=controller_estimate,
                previous_node_action=previous_node_action,
                soc=current_soc,
                warm_start=True,
            )
            if not result.solution.feasible:
                raise RuntimeError(result.solution.message)
            coordinate_action = result.solution.coordinate_action
            node_action = result.solution.node_action
            total_input = disturbance + coordinate_action
            model_output = output_matrix @ state + feedthrough @ total_input
            delivered_output = model_output + mismatch @ model_output
            state = state_matrix @ state + input_matrix @ total_input
            current_soc = _advance_soc(current_soc, node_action, limits)
            outputs[step] = delivered_output
            coordinate_actions[step] = coordinate_action
            node_actions[step] = node_action
            soc_history[step + 1] = current_soc
            previous_output = delivered_output
            previous_coordinate_action = coordinate_action
            previous_node_action = node_action
            maximum_residual = max(maximum_residual, result.solution.maximum_constraint_residual)
            maximum_primal_ratio = max(maximum_primal_ratio, result.primal_residual_ratio)
            maximum_dual_ratio = max(maximum_dual_ratio, result.dual_residual_ratio)
            maximum_iterations = max(maximum_iterations, result.solution.solver_iterations)
    except (RuntimeError, ValueError) as exc:
        return {
            **base_row,
            "solver_failed": True,
            "execution_error": False,
            "error": str(exc),
        }

    ramp = np.vstack((node_actions[:1], np.diff(node_actions, axis=0)))
    violations = int(
        np.any(~np.isfinite(outputs))
        or np.any(~np.isfinite(coordinate_actions))
        or np.any(~np.isfinite(node_actions))
        or np.any(np.abs(node_actions) > limits.node_power + 1.0e-8)
        or np.any(np.abs(ramp) > limits.node_ramp + 1.0e-8)
        or np.any(soc_history < limits.minimum_soc - 1.0e-8)
        or np.any(soc_history > limits.maximum_soc + 1.0e-8)
    )
    output_energy = float(np.sum(np.square(outputs)))
    return {
        **base_row,
        "solver_failed": False,
        "execution_error": False,
        "zero_output_energy": zero_energy,
        "output_energy": output_energy,
        "output_energy_ratio": output_energy / zero_energy,
        "coordinate_action_energy": float(np.sum(np.square(coordinate_actions))),
        "maximum_node_power": float(np.max(np.abs(node_actions))),
        "maximum_node_ramp": float(np.max(np.abs(ramp))),
        "minimum_soc": float(np.min(soc_history)),
        "maximum_soc": float(np.max(soc_history)),
        "maximum_solver_iterations": maximum_iterations,
        "maximum_constraint_residual": maximum_residual,
        "maximum_primal_residual_ratio": maximum_primal_ratio,
        "maximum_dual_residual_ratio": maximum_dual_ratio,
        "constraint_violation_count": violations,
    }


def _evaluate_task(task: HoldoutTask) -> tuple[int, dict[str, object]]:
    if (
        any(
            value is None
            for value in (
                _WORKER_PLANTS,
                _WORKER_CONTROLLERS,
                _WORKER_ESTIMATORS,
                _WORKER_TRANSFORMS,
            )
        )
        or _WORKER_NATIVE_THREAD_LIMIT_VALID is None
    ):
        raise RuntimeError("R330 worker is not initialized")
    case = task.case
    return task.index, _simulate_holdout_row(
        _WORKER_PLANTS[case.point],
        _WORKER_CONTROLLERS[case.point],
        _WORKER_ESTIMATORS[case.point],
        case,
        task.mismatch_name,
        _WORKER_TRANSFORMS[task.mismatch_name],
        task.phase,
        _WORKER_NATIVE_THREAD_LIMIT_VALID,
    )


def _parallel_pass(
    plants: dict[str, Any],
    controllers: dict[str, Any],
    estimators: dict[str, DisturbanceEstimatorDesign],
    *,
    cases: list[Any],
    transforms: dict[str, np.ndarray],
    phase: str,
    maximum_workers: int,
) -> list[dict[str, object]]:
    tasks = [
        HoldoutTask(index, case, mismatch_name, phase)
        for index, (case, mismatch_name) in enumerate(
            (case, mismatch_name) for case in cases for mismatch_name in transforms
        )
    ]
    with ProcessPoolExecutor(
        max_workers=maximum_workers,
        mp_context=mp.get_context("spawn"),
        initializer=_initialize_worker,
        initargs=(plants, controllers, estimators, transforms),
    ) as pool:
        indexed = list(pool.map(_evaluate_task, tasks, chunksize=1))
    indexed.sort(key=lambda item: item[0])
    return [row for _index, row in indexed]


def _holdout_pass(
    plants: dict[str, Any],
    controllers: dict[str, Any],
    estimators: dict[str, DisturbanceEstimatorDesign],
) -> list[dict[str, object]]:
    return _parallel_pass(
        plants,
        controllers,
        estimators,
        cases=r329.r328.r326.r325.holdout_cases(),
        transforms=r329.r328.r326.r325.mismatch_transforms(),
        phase="holdout",
        maximum_workers=HOLDOUT_WORKERS,
    )


def execute(seal_path: Path, expected: str, out_dir: Path) -> str:
    seal, seal_digest = _load_seal(seal_path, expected)
    plants, controllers, estimators = _formal_designs()
    design_fingerprints = _design_fingerprints(plants, controllers, estimators)
    mismatch_fingerprints = _mismatch_records()
    holdout_case_records = _case_records()
    limits = _limits_record()
    runtime_fingerprint = _runtime_dependency_fingerprint()
    if (
        design_fingerprints != seal["contract"]["frozen_design_fingerprints"]
        or mismatch_fingerprints != seal["contract"]["mismatch_fingerprints"]
        or holdout_case_records != seal["contract"]["holdout_case_records"]
        or limits != seal["contract"]["limits"]
        or runtime_fingerprint != seal["contract"]["runtime_dependency_fingerprint"]
    ):
        raise RuntimeError("frozen design, case, mismatch, or limit drift before holdout")
    created_utc = datetime.now(UTC).isoformat()
    receipt = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": created_utc,
        "status": "HOLDOUT-OPENED",
        "seal_sha256": seal_digest,
        "contract_payload_sha256": seal["contract_payload_sha256"],
        "parent_execution_sha256": seal["parent"]["r329_execution"]["sha256"],
        "parent_analysis_sha256": seal["parent"]["r329_analysis"]["sha256"],
    }
    receipt_digest = _write_new_json(out_dir / "execution_receipt.json", receipt)
    first = _holdout_pass(plants, controllers, estimators)
    second = _holdout_pass(plants, controllers, estimators)
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": created_utc,
        "seal_sha256": seal_digest,
        "execution_receipt_sha256": receipt_digest,
        "contract_payload_sha256": seal["contract_payload_sha256"],
        "parent_execution_sha256": seal["parent"]["r329_execution"]["sha256"],
        "parent_analysis_sha256": seal["parent"]["r329_analysis"]["sha256"],
        "sealed_source_identity": True,
        "parent_identity": True,
        "development_identity": True,
        "design_fingerprint_identity": True,
        "mismatch_identity": True,
        "holdout_case_identity": True,
        "limits_identity": True,
        "runtime_dependency_identity": True,
        "estimator_information_boundary": r329._information_boundary_valid(),
        "deterministic_execution_replay": (_canonical_bytes(first) == _canonical_bytes(second)),
        "design_fingerprints": design_fingerprints,
        "mismatch_fingerprints": mismatch_fingerprints,
        "holdout_case_records": holdout_case_records,
        "limits": limits,
        "runtime_dependency_fingerprint": runtime_fingerprint,
        "rows": first,
        "eval": "NOT-APPLICABLE-DETERMINISTIC-MODEL-ONLY",
        "physical_execution_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }
    return _write_new_json(out_dir / "execution.json", payload)


def analyse(seal_path: Path, expected: str, out_dir: Path) -> dict[str, str]:
    seal, seal_digest = _load_seal(seal_path, expected)
    receipt, receipt_digest = r329.r328.r326.r325._read_verified_json(
        out_dir / "execution_receipt.json"
    )
    execution, execution_digest = r329.r328.r326.r325._read_verified_json(
        out_dir / "execution.json"
    )
    execution_view = dict(execution)
    execution_view["execution_sha256"] = execution_digest
    execution_view["execution_receipt_identity"] = bool(
        receipt.get("round") == ROUND_ID
        and receipt.get("question") == QUESTION_ID
        and receipt.get("status") == "HOLDOUT-OPENED"
        and receipt.get("seal_sha256") == seal_digest
        and receipt.get("contract_payload_sha256") == seal["contract_payload_sha256"]
        and receipt.get("parent_execution_sha256") == seal["parent"]["r329_execution"]["sha256"]
        and receipt.get("parent_analysis_sha256") == seal["parent"]["r329_analysis"]["sha256"]
        and execution.get("execution_receipt_sha256") == receipt_digest
    )
    execution_view["sealed_source_identity"] = bool(
        execution.get("sealed_source_identity") is True
        and execution.get("seal_sha256") == seal_digest
        and execution.get("contract_payload_sha256") == seal["contract_payload_sha256"]
    )
    execution_view["parent_identity"] = bool(
        execution.get("parent_identity") is True
        and execution.get("parent_execution_sha256") == seal["parent"]["r329_execution"]["sha256"]
        and execution.get("parent_analysis_sha256") == seal["parent"]["r329_analysis"]["sha256"]
    )
    execution_view["development_identity"] = bool(
        execution.get("development_identity") is True and execution_view["parent_identity"] is True
    )
    execution_view["design_fingerprint_identity"] = bool(
        execution.get("design_fingerprint_identity") is True
        and execution.get("design_fingerprints") == seal["contract"]["frozen_design_fingerprints"]
    )
    execution_view["mismatch_identity"] = bool(
        execution.get("mismatch_identity") is True
        and execution.get("mismatch_fingerprints") == seal["contract"]["mismatch_fingerprints"]
    )
    execution_view["holdout_case_identity"] = bool(
        execution.get("holdout_case_identity") is True
        and execution.get("holdout_case_records") == seal["contract"]["holdout_case_records"]
    )
    execution_view["limits_identity"] = bool(
        execution.get("limits_identity") is True
        and execution.get("limits") == seal["contract"]["limits"]
    )
    execution_view["runtime_dependency_identity"] = bool(
        execution.get("runtime_dependency_identity") is True
        and execution.get("runtime_dependency_fingerprint")
        == seal["contract"]["runtime_dependency_fingerprint"]
    )
    first = analyse_r330_holdout(execution_view, seal["contract"], analysis_replay=True)
    second = analyse_r330_holdout(execution_view, seal["contract"], analysis_replay=True)
    deterministic = _canonical_bytes(first) == _canonical_bytes(second)
    if not deterministic:
        first = analyse_r330_holdout(execution_view, seal["contract"], analysis_replay=False)
    analysis_digest = _write_new_json(out_dir / "analysis.json", first)
    provenance = {
        "round": ROUND_ID,
        "seal_sha256": seal_digest,
        "execution_receipt_sha256": receipt_digest,
        "execution_sha256": execution_digest,
        "analysis_sha256": analysis_digest,
        "sources": seal["sources"],
        "parent": seal["parent"],
    }
    provenance_digest = _write_new_json(out_dir / "provenance.json", provenance)
    manifest = {
        "round": ROUND_ID,
        "classification": first["classification"],
        "files": {
            "execution_receipt.json": receipt_digest,
            "execution.json": execution_digest,
            "analysis.json": analysis_digest,
            "provenance.json": provenance_digest,
        },
    }
    manifest_digest = _write_new_json(out_dir / "run_manifest.json", manifest)
    return {
        "classification": str(first["classification"]),
        "execution_receipt_sha256": receipt_digest,
        "execution_sha256": execution_digest,
        "analysis_sha256": analysis_digest,
        "provenance_sha256": provenance_digest,
        "run_manifest_sha256": manifest_digest,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "execute", "analyse"))
    parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    parser.add_argument("--expected-seal-sha256")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "prepare":
        print(prepare(args.seal))
        return 0
    if not args.expected_seal_sha256:
        raise SystemExit("--expected-seal-sha256 is required after prepare")
    if args.command == "execute":
        print(execute(args.seal, args.expected_seal_sha256, args.out))
        return 0
    print(json.dumps(analyse(args.seal, args.expected_seal_sha256, args.out), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
