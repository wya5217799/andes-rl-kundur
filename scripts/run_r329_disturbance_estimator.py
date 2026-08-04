"""Prepare, execute, and analyse the R329 fixed estimator repair."""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import multiprocessing as mp
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple

import numpy as np
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
for import_root in (ROOT, ROOT / "src"):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

import scripts.run_r328_estimation_cause as r328  # noqa: E402
from probes.r329_disturbance_estimator import analyse_r329_estimator  # noqa: E402

from andes_rl_kundur.control.model_first_constrained_horizon import (  # noqa: E402
    _advance_soc,
)
from andes_rl_kundur.control.model_first_constrained_qp import (  # noqa: E402
    SparseConstrainedHorizonSolver,
    simulate_sparse_constrained_horizon_feedback,
)
from andes_rl_kundur.control.model_first_disturbance_estimator import (  # noqa: E402
    DisturbanceEstimatorDesign,
    advance_disturbance_estimate,
    synthesize_disturbance_estimator,
)
from andes_rl_kundur.control.model_first_offline_feedback import (  # noqa: E402
    FeedbackLimits,
)

ROUND_ID = "R329"
QUESTION_ID = "Q-0082"
R326_EXECUTION = ROOT / "results/r326_solver_adequacy/execution.json"
R327_ANALYSIS = ROOT / "results/r327_reference_recovery/analysis.json"
R328_SEAL = ROOT / "memory/rounds/R328/estimation_cause_seal.json"
R328_EXECUTION = ROOT / "results/r328_estimation_cause/execution.json"
R328_ANALYSIS = ROOT / "results/r328_estimation_cause/analysis.json"
R328_PROVENANCE = ROOT / "results/r328_estimation_cause/provenance.json"
R328_MANIFEST = ROOT / "results/r328_estimation_cause/run_manifest.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R329/disturbance_estimator_seal.json"
DEFAULT_OUT = ROOT / "results/r329_disturbance_estimator"
DEVELOPMENT_WORKERS = min(8, os.cpu_count() or 1)

_WORKER_PLANTS: dict[str, Any] | None = None
_WORKER_CONTROLLERS: dict[str, Any] | None = None
_WORKER_ESTIMATORS: dict[str, DisturbanceEstimatorDesign] | None = None
_WORKER_PARENT_RATIOS: dict[str, float] | None = None
_WORKER_ORACLE_RATIOS: dict[str, float] | None = None
_THREAD_LIMITER: Any = None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path_text(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


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
    return r328._write_new_json(path, payload)


def build_contract() -> dict[str, object]:
    parent = r328._r326_contract()
    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "model-only-fixed-disturbance-aware-estimator",
        "parent_round": "R328",
        "points": ["HS0", "HS1"],
        "development_case_count": 32,
        "solver": deepcopy(parent["solver"]),
        "gates": {
            "development_mean_output_energy_ratio_maximum": parent["gates"][
                "development_mean_output_energy_ratio_maximum"
            ],
            "development_worst_output_energy_ratio_maximum": parent["gates"][
                "development_worst_output_energy_ratio_maximum"
            ],
        },
        "estimator": {
            "kind": "fixed-disturbance-augmented-steady-state",
            "candidate_count": 1,
            "augmented_order": 14,
            "disturbance_model": "random-walk-prior",
            "disturbance_scale": 0.05,
            "measurement_fraction": 0.01,
            "covariance_floor": "trace-scaled-1e-12",
            "maximum_normalized_covariance_residual": 1.0e-8,
            "minimum_covariance_eigenvalue": -1.0e-12,
            "maximum_error_pole_radius": 1.0,
            "maximum_constraint_residual": 1.0e-8,
            "maximum_normalized_solver_residual_ratio": 1.0,
            "information": [
                "previous-delivered-output",
                "previous-executed-coordinate-action",
                "internal-estimator-memory",
                "frozen-retained-model-matrices",
            ],
            "forbidden_information": [
                "true-state",
                "true-disturbance",
                "current-output",
                "future-information",
            ],
            "development_workers": DEVELOPMENT_WORKERS,
            "native_numerical_threads_per_worker": 1,
            "holdout_access": "forbidden",
        },
        "comparison_identifiability": {
            "decision": "ALLOW",
            "estimand": "fixed-estimator-development-repair-and-state-error-change",
            "oracle_role": "read-only-upper-comparator",
        },
        "classification": [
            "INVALID-AUGMENTED-ESTIMATOR",
            "AUGMENTED-ESTIMATOR-NO-GO",
            "AUGMENTED-ESTIMATOR-DEVELOPMENT-PASS",
        ],
        "eval": "NOT-APPLICABLE-DETERMINISTIC-MODEL-ONLY",
        "physical_execution_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R329/plan.md",
        "question": ROOT / "memory/questions/Q-0082.md",
        "r326_execution": R326_EXECUTION,
        "r327_analysis": R327_ANALYSIS,
        "r328_seal": R328_SEAL,
        "r328_execution": R328_EXECUTION,
        "r328_analysis": R328_ANALYSIS,
        "r328_provenance": R328_PROVENANCE,
        "r328_manifest": R328_MANIFEST,
        "r328_claim": ROOT / "memory/claims/CLM-0850.md",
        "r328_feed": ROOT / "paper/decoupling_marl_model_first/reports/R328.md",
        "controller_module": (ROOT / "src/andes_rl_kundur/control/model_first_constrained_qp.py"),
        "estimator_module": (
            ROOT / "src/andes_rl_kundur/control/model_first_disturbance_estimator.py"
        ),
        "validation_probe": ROOT / "probes/r329_disturbance_estimator.py",
        "adapter": ROOT / "scripts/run_r329_disturbance_estimator.py",
        "estimator_tests": ROOT / "tests/test_model_first_disturbance_estimator.py",
        "validation_tests": ROOT / "tests/test_r329_disturbance_estimator.py",
        "adapter_tests": ROOT / "tests/test_r329_disturbance_estimator_adapter.py",
        "project_dependencies": ROOT / "pyproject.toml",
        "artifact_io": ROOT / "memory/tools/artifact_io.py",
    }


def _sources() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _path_text(path), "sha256": _sha256_file(path)}
        for name, path in _source_paths().items()
    }


def _parent_bundle() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    r326_execution, r326_digest = r328.r326.r325._read_verified_json(R326_EXECUTION)
    r327_analysis, r327_digest = r328.r326.r325._read_verified_json(R327_ANALYSIS)
    r328_seal, r328_seal_digest = r328.r326.r325._read_verified_json(R328_SEAL)
    r328_execution, r328_execution_digest = r328.r326.r325._read_verified_json(R328_EXECUTION)
    r328_analysis, r328_analysis_digest = r328.r326.r325._read_verified_json(R328_ANALYSIS)
    _provenance, provenance_digest = r328.r326.r325._read_verified_json(R328_PROVENANCE)
    _manifest, manifest_digest = r328.r326.r325._read_verified_json(R328_MANIFEST)
    if (
        r328_analysis.get("classification") != "ESTIMATION-LAYER-CAUSE"
        or r328_analysis.get("exact_state", {}).get("valid") is not True
        or r328_analysis.get("holdout_accessed") is not False
        or r327_analysis.get("classification") != "DEVELOPMENT-NO-GO"
        or r327_analysis.get("arms", {})
        .get("retained_cross", {})
        .get("development", {})
        .get("valid")
        is not True
        or r326_execution.get("holdout_accessed") is not False
    ):
        raise RuntimeError("R326-R328 parents do not authorize R329")
    parent = {
        "r326_execution": {"path": _path_text(R326_EXECUTION), "sha256": r326_digest},
        "r327_analysis": {"path": _path_text(R327_ANALYSIS), "sha256": r327_digest},
        "r328_seal": {"path": _path_text(R328_SEAL), "sha256": r328_seal_digest},
        "r328_execution": {
            "path": _path_text(R328_EXECUTION),
            "sha256": r328_execution_digest,
        },
        "r328_analysis": {
            "path": _path_text(R328_ANALYSIS),
            "sha256": r328_analysis_digest,
        },
        "r328_provenance": {
            "path": _path_text(R328_PROVENANCE),
            "sha256": provenance_digest,
        },
        "r328_manifest": {
            "path": _path_text(R328_MANIFEST),
            "sha256": manifest_digest,
        },
        "r328_contract_payload_sha256": r328_seal["contract_payload_sha256"],
    }
    return r326_execution, r328_execution, parent


def prepare(seal_path: Path) -> str:
    _r326_execution, _r328_execution, parent = _parent_bundle()
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
    seal, digest = r328.r326.r325._read_verified_json(path, expected)
    _r326_execution, _r328_execution, parent = _parent_bundle()
    contract = build_contract()
    if (
        seal.get("round") != ROUND_ID
        or seal.get("question") != QUESTION_ID
        or seal.get("contract") != contract
        or seal.get("contract_payload_sha256") != _payload_sha256(contract)
        or seal.get("parent") != parent
        or seal.get("sources") != _sources()
    ):
        raise RuntimeError("R329 seal contract, parent, or source drift")
    return seal, digest


def _formal_designs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    plants, controllers = r328._retained_models_and_designs()
    estimators = {
        point: synthesize_disturbance_estimator(
            plants[point],
            output_scales=controllers[point].output_scales,
            disturbance_scale=0.05,
            measurement_fraction=0.01,
        )
        for point in plants
    }
    return plants, controllers, estimators


def _design_records(
    estimators: dict[str, DisturbanceEstimatorDesign],
) -> dict[str, dict[str, object]]:
    return {
        point: {
            "augmented_order": design.transition_matrix.shape[0],
            "observability_rank": design.observability_rank,
            "finite": all(
                np.all(np.isfinite(value))
                for value in (
                    design.transition_matrix,
                    design.measurement_matrix,
                    design.filter_gain,
                    design.covariance,
                )
            ),
            "covariance_positive_semidefinite": (design.covariance_minimum_eigenvalue >= -1.0e-12),
            "covariance_symmetry_error": design.covariance_symmetry_error,
            "covariance_minimum_eigenvalue": design.covariance_minimum_eigenvalue,
            "normalized_covariance_residual": design.normalized_covariance_residual,
            "error_pole_radius": design.error_pole_radius,
        }
        for point, design in estimators.items()
    }


def _ratio_maps() -> tuple[dict[str, float], dict[str, float]]:
    r326_execution, r328_execution, _parent = _parent_bundle()
    parent_rows = r326_execution["arms"]["retained_cross"]["rows"]["development"]
    parent = {str(row["case"]): float(row["output_energy_ratio"]) for row in parent_rows}
    oracle = {str(row["case"]): float(row["output_energy_ratio"]) for row in r328_execution["rows"]}
    if set(parent) != set(oracle) or len(parent) != 32:
        raise RuntimeError("parent and oracle case inventories differ")
    return parent, oracle


def _information_boundary_valid() -> bool:
    return set(inspect.signature(advance_disturbance_estimate).parameters) == {
        "design",
        "prior_estimate",
        "previous_delivered_output",
        "previous_executed_action",
    }


class EvaluationTask(NamedTuple):
    index: int
    case: Any


def _initialize_worker(
    plants: dict[str, Any],
    controllers: dict[str, Any],
    estimators: dict[str, DisturbanceEstimatorDesign],
    parent_ratios: dict[str, float],
    oracle_ratios: dict[str, float],
) -> None:
    global _WORKER_PLANTS, _WORKER_CONTROLLERS, _WORKER_ESTIMATORS
    global _WORKER_PARENT_RATIOS, _WORKER_ORACLE_RATIOS, _THREAD_LIMITER
    _THREAD_LIMITER = threadpool_limits(limits=1)
    _WORKER_PLANTS = plants
    _WORKER_CONTROLLERS = controllers
    _WORKER_ESTIMATORS = estimators
    _WORKER_PARENT_RATIOS = parent_ratios
    _WORKER_ORACLE_RATIOS = oracle_ratios


def _true_state_squared_error(plant: Any, case: Any, trace: Any) -> float:
    base = trace.base
    state_matrix = np.asarray(plant.state_matrix, dtype=float)
    input_matrix = np.asarray(plant.input_matrix, dtype=float)
    state = np.zeros(state_matrix.shape[0])
    previous_output = np.zeros(4)
    error = 0.0
    for step, disturbance in enumerate(np.asarray(case.disturbance, dtype=float)):
        exact = np.concatenate((state, previous_output))
        error += float(np.sum(np.square(base.estimates[step] - exact)))
        total_input = disturbance + base.coordinate_actions[step]
        state = state_matrix @ state + input_matrix @ total_input
        previous_output = base.outputs[step]
    return error


def _simulate_case(
    plant: Any,
    controller: Any,
    estimator: DisturbanceEstimatorDesign,
    case: Any,
    parent_ratio: float,
    oracle_ratio: float,
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
    state_error = 0.0
    maximum_state_error = 0.0
    maximum_residual = 0.0
    maximum_primal_ratio = 0.0
    maximum_dual_ratio = 0.0
    maximum_iterations = 0
    try:
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
            exact = np.concatenate((state, previous_output))
            difference = controller_estimate - exact
            state_error += float(np.sum(np.square(difference)))
            maximum_state_error = max(maximum_state_error, float(np.max(np.abs(difference))))
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
            output = output_matrix @ state + feedthrough @ total_input
            state = state_matrix @ state + input_matrix @ total_input
            current_soc = _advance_soc(current_soc, node_action, limits)
            outputs[step] = output
            coordinate_actions[step] = coordinate_action
            node_actions[step] = node_action
            soc_history[step + 1] = current_soc
            previous_output = output
            previous_coordinate_action = coordinate_action
            previous_node_action = node_action
            maximum_residual = max(maximum_residual, result.solution.maximum_constraint_residual)
            maximum_primal_ratio = max(maximum_primal_ratio, result.primal_residual_ratio)
            maximum_dual_ratio = max(maximum_dual_ratio, result.dual_residual_ratio)
            maximum_iterations = max(maximum_iterations, result.solution.solver_iterations)
    except (RuntimeError, ValueError) as exc:
        return {
            "arm": "retained_cross",
            "phase": "development",
            "case": case.name,
            "solver_failed": True,
            "execution_error": False,
            "error": str(exc),
        }

    parent_trace = simulate_sparse_constrained_horizon_feedback(
        plant,
        disturbances,
        design=controller,
        initial_soc=case.initial_soc,
        limits=limits,
    )
    parent_zero = r328.r326.r325._zero_energy(plant, case, np.zeros((4, 4)))
    parent_replay_ratio = parent_trace.base.output_energy / parent_zero
    parent_state_error = _true_state_squared_error(plant, case, parent_trace)
    ramp = np.vstack((node_actions[:1], np.diff(node_actions, axis=0)))
    violations = int(
        np.any(~np.isfinite(outputs))
        or np.any(~np.isfinite(node_actions))
        or np.any(np.abs(node_actions) > limits.node_power + 1.0e-8)
        or np.any(np.abs(ramp) > limits.node_ramp + 1.0e-8)
        or np.any(soc_history < limits.minimum_soc - 1.0e-8)
        or np.any(soc_history > limits.maximum_soc + 1.0e-8)
    )
    output_energy = float(np.sum(np.square(outputs)))
    return {
        "arm": "retained_cross",
        "phase": "development",
        "case": case.name,
        "solver_failed": False,
        "execution_error": False,
        "zero_output_energy": parent_zero,
        "output_energy": output_energy,
        "output_energy_ratio": output_energy / parent_zero,
        "parent_output_energy_ratio": parent_ratio,
        "parent_replay_output_energy_ratio": parent_replay_ratio,
        "parent_output_identity": abs(parent_replay_ratio - parent_ratio) <= 1.0e-12,
        "oracle_output_energy_ratio": oracle_ratio,
        "state_estimation_squared_error": state_error,
        "parent_state_estimation_squared_error": parent_state_error,
        "maximum_state_estimation_error": maximum_state_error,
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


def _evaluate_task(task: EvaluationTask) -> tuple[int, dict[str, object]]:
    if any(
        value is None
        for value in (
            _WORKER_PLANTS,
            _WORKER_CONTROLLERS,
            _WORKER_ESTIMATORS,
            _WORKER_PARENT_RATIOS,
            _WORKER_ORACLE_RATIOS,
        )
    ):
        raise RuntimeError("R329 worker is not initialized")
    case = task.case
    return task.index, _simulate_case(
        _WORKER_PLANTS[case.point],
        _WORKER_CONTROLLERS[case.point],
        _WORKER_ESTIMATORS[case.point],
        case,
        _WORKER_PARENT_RATIOS[case.name],
        _WORKER_ORACLE_RATIOS[case.name],
    )


def _development_pass(
    plants: dict[str, Any],
    controllers: dict[str, Any],
    estimators: dict[str, DisturbanceEstimatorDesign],
) -> list[dict[str, object]]:
    parent_ratios, oracle_ratios = _ratio_maps()
    tasks = [
        EvaluationTask(index, case) for index, case in enumerate(r328.r326.r325.development_cases())
    ]
    with ProcessPoolExecutor(
        max_workers=DEVELOPMENT_WORKERS,
        mp_context=mp.get_context("spawn"),
        initializer=_initialize_worker,
        initargs=(plants, controllers, estimators, parent_ratios, oracle_ratios),
    ) as pool:
        indexed = list(pool.map(_evaluate_task, tasks, chunksize=1))
    indexed.sort(key=lambda item: item[0])
    return [row for _index, row in indexed]


def execute(seal_path: Path, expected: str, out_dir: Path) -> str:
    seal, seal_digest = _load_seal(seal_path, expected)
    plants, controllers, estimators = _formal_designs()
    first = _development_pass(plants, controllers, estimators)
    second = _development_pass(plants, controllers, estimators)
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": seal_digest,
        "contract_payload_sha256": seal["contract_payload_sha256"],
        "parent_execution_sha256": seal["parent"]["r326_execution"]["sha256"],
        "parent_analysis_sha256": seal["parent"]["r327_analysis"]["sha256"],
        "oracle_execution_sha256": seal["parent"]["r328_execution"]["sha256"],
        "sealed_source_identity": True,
        "parent_identity": True,
        "oracle_identity": True,
        "estimator_information_boundary": _information_boundary_valid(),
        "deterministic_execution_replay": (_canonical_bytes(first) == _canonical_bytes(second)),
        "holdout_accessed": False,
        "parent_output_feedback_valid_failed": True,
        "designs": _design_records(estimators),
        "rows": first,
        "eval": "NOT-APPLICABLE-DETERMINISTIC-MODEL-ONLY",
        "physical_execution_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }
    return _write_new_json(out_dir / "execution.json", payload)


def analyse(seal_path: Path, expected: str, out_dir: Path) -> dict[str, str]:
    seal, seal_digest = _load_seal(seal_path, expected)
    execution, execution_digest = r328.r326.r325._read_verified_json(out_dir / "execution.json")
    execution_view = dict(execution)
    execution_view["execution_sha256"] = execution_digest
    first = analyse_r329_estimator(execution_view, seal["contract"], analysis_replay=True)
    second = analyse_r329_estimator(execution_view, seal["contract"], analysis_replay=True)
    deterministic = _canonical_bytes(first) == _canonical_bytes(second)
    if not deterministic:
        first = analyse_r329_estimator(execution_view, seal["contract"], analysis_replay=False)
    analysis_digest = _write_new_json(out_dir / "analysis.json", first)
    provenance = {
        "round": ROUND_ID,
        "seal_sha256": seal_digest,
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
            "execution.json": execution_digest,
            "analysis.json": analysis_digest,
            "provenance.json": provenance_digest,
        },
    }
    manifest_digest = _write_new_json(out_dir / "run_manifest.json", manifest)
    return {
        "classification": str(first["classification"]),
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
