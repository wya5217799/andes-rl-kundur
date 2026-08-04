"""Prepare, execute, and analyse the prospective R326 solver-only repair.

The adapter preserves the R325 controller and case contracts, replays every
development prefix reached by the old solver, executes the sparse-QP candidate
with isolated case workspaces, and opens the unchanged conditional holdout
only after the pure validation probe admits it.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import multiprocessing as mp
import os
import platform
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple

import numpy as np
import osqp
import scipy
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
for import_root in (ROOT, ROOT / "src"):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

import scripts.run_r325_constrained_horizon as r325  # noqa: E402
from probes.r326_solver_adequacy import (  # noqa: E402
    analyse_r326_execution,
    solver_development_allows_holdout,
)

from andes_rl_kundur.control.model_first_constrained_horizon import (  # noqa: E402
    ConstrainedHorizonInfeasible,
    _advance_soc,
    _prediction_matrices,
    solve_constrained_horizon_action,
)
from andes_rl_kundur.control.model_first_constrained_qp import (  # noqa: E402
    SparseConstrainedHorizonSolver,
    simulate_sparse_constrained_horizon_feedback,
)
from andes_rl_kundur.control.model_first_offline_feedback import (  # noqa: E402
    FeedbackLimits,
)

ROUND_ID = "R326"
QUESTION_ID = "Q-0080"
R325_SEAL = ROOT / "memory/rounds/R325/constrained_horizon_seal.json"
R325_EXECUTION = ROOT / "results/r325_constrained_horizon/execution.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R326/solver_adequacy_seal.json"
DEFAULT_OUT = ROOT / "results/r326_solver_adequacy"
DEVELOPMENT_WORKERS = min(8, os.cpu_count() or 1)
HOLDOUT_WORKERS = min(4, os.cpu_count() or 1)

_WORKER_PLANTS: dict[str, Any] | None = None
_WORKER_DESIGNS: dict[str, dict[str, Any]] | None = None
_WORKER_R325_STATUS: dict[tuple[str, str, str], dict[str, Any]] | None = None
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
    return r325._write_new_json(path, payload)


def _distribution_hash(name: str) -> str:
    distribution = importlib.metadata.distribution(name)
    digest = hashlib.sha256()
    digest.update(b"python-distribution-v1\0")
    files = sorted(distribution.files or (), key=lambda item: str(item).replace("\\", "/"))
    for item in files:
        path = Path(distribution.locate_file(item))
        if not path.is_file():
            raise RuntimeError(f"installed distribution file is missing: {item}")
        relative = str(item).replace("\\", "/").encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(bytes.fromhex(_sha256_file(path)))
    return digest.hexdigest()


def dependency_fingerprint() -> dict[str, object]:
    """Return a path-independent fingerprint of the numerical runtime."""

    executable = Path(sys.executable).resolve()
    return {
        "python_version": platform.python_version(),
        "python_executable_sha256": _sha256_file(executable),
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "osqp_version": osqp.__version__,
        "osqp_algebra": osqp.default_algebra(),
        "osqp_distribution_sha256": _distribution_hash("osqp"),
    }


def _solver_contract() -> dict[str, object]:
    return {
        "name": "osqp",
        "version": "1.1.3",
        "algebra": "builtin",
        "linear_solver": "direct",
        "maximum_iterations": 20_000,
        "absolute_tolerance": 1.0e-9,
        "relative_tolerance": 1.0e-9,
        "feasibility_tolerance": 1.0e-8,
        "polishing": False,
        "warm_starting": True,
        "adaptive_rho": True,
        "adaptive_rho_interval": 25,
        "scaled_termination": False,
        "check_termination": 25,
        "accepted_status": "solved",
        "workspace_scope": "fresh-per-case-reused-within-case",
    }


def _r325_contract_identity() -> tuple[dict[str, Any], str, str]:
    seal, seal_digest = r325._read_verified_json(R325_SEAL)
    contract = r325.build_contract()
    contract_digest = _payload_sha256(contract)
    if (
        seal.get("round") != "R325"
        or seal.get("contract") != contract
        or seal.get("contract_payload_sha256") != contract_digest
    ):
        raise RuntimeError("R325 controller contract no longer matches its sealed payload")
    return contract, contract_digest, seal_digest


def build_contract() -> dict[str, Any]:
    parent, parent_digest, _seal_digest = _r325_contract_identity()
    contract = deepcopy(parent)
    contract["round"] = ROUND_ID
    contract["question"] = QUESTION_ID
    contract["solver"] = _solver_contract()
    contract["solver_repair"] = {
        "single_factor": "slsqp-to-osqp-numerical-implementation",
        "prefix_action_absolute_tolerance": 2.0e-5,
        "prefix_output_absolute_tolerance": 1.0e-6,
        "maximum_normalized_residual_ratio": 1.0,
        "minimum_action_hessian_eigenvalue": 0.0,
        "r325_contract_payload_sha256": parent_digest,
        "dependency_fingerprint": dependency_fingerprint(),
        "development_workers": DEVELOPMENT_WORKERS,
        "holdout_workers": HOLDOUT_WORKERS,
        "reference_scope": "all-successful-r325-slsqp-development-prefix-samples",
        "holdout_access": "conditional-after-replayed-development-admission",
    }
    contract["classification"] = [
        "INVALID-SOLVER-REPAIR",
        "SOLVER-REPAIR-NO-GO",
        "DEVELOPMENT-NO-GO",
        "FRESH-HOLDOUT-NO-GO",
        "RETAINED-BLOCK-NO-VALUE",
        "CONSTRAINED-HORIZON-PASS",
    ]
    return contract


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R326/plan.md",
        "question": ROOT / "memory/questions/Q-0080.md",
        "r325_seal": R325_SEAL,
        "r325_execution": R325_EXECUTION,
        "r325_adapter": ROOT / "scripts/run_r325_constrained_horizon.py",
        "r325_validation_probe": ROOT / "probes/r325_constrained_horizon_validation.py",
        "solver_module": ROOT / "src/andes_rl_kundur/control/model_first_constrained_qp.py",
        "validation_probe": ROOT / "probes/r326_solver_adequacy.py",
        "adapter": ROOT / "scripts/run_r326_solver_adequacy.py",
        "solver_tests": ROOT / "tests/test_model_first_constrained_qp.py",
        "validation_tests": ROOT / "tests/test_r326_solver_adequacy.py",
        "adapter_tests": ROOT / "tests/test_r326_solver_adequacy_adapter.py",
        "project_dependencies": ROOT / "pyproject.toml",
        "artifact_io": ROOT / "memory/tools/artifact_io.py",
    }


def _sources() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _path_text(path), "sha256": _sha256_file(path)}
        for name, path in _source_paths().items()
    }


def prepare(seal_path: Path) -> str:
    parent, model_digest, _analysis, analysis_digest = r325._load_parent()
    r325_contract, r325_contract_digest, r325_seal_digest = _r325_contract_identity()
    r325_execution, r325_execution_digest = r325._read_verified_json(R325_EXECUTION)
    if r325_execution.get("holdout_accessed") is not False:
        raise RuntimeError("R325 conditional holdout is not fresh")
    contract = build_contract()
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": _payload_sha256(contract),
        "parent": {
            "dynamic_model": {
                "path": r325._path_text(r325.PARENT_MODEL),
                "sha256": model_digest,
            },
            "analysis": {
                "path": r325._path_text(r325.PARENT_ANALYSIS),
                "sha256": analysis_digest,
            },
            "r325_seal": {"path": _path_text(R325_SEAL), "sha256": r325_seal_digest},
            "r325_execution": {
                "path": _path_text(R325_EXECUTION),
                "sha256": r325_execution_digest,
            },
            "r325_contract_payload_sha256": r325_contract_digest,
            "r325_contract": r325_contract,
        },
        "sources": _sources(),
    }
    return _write_new_json(seal_path, seal)


def _load_seal(path: Path, expected: str) -> tuple[dict[str, Any], str]:
    seal, digest = r325._read_verified_json(path, expected)
    _parent, model_digest, _analysis, analysis_digest = r325._load_parent()
    r325_contract, r325_contract_digest, r325_seal_digest = _r325_contract_identity()
    _r325_execution, r325_execution_digest = r325._read_verified_json(R325_EXECUTION)
    expected_parent = {
        "dynamic_model": {
            "path": r325._path_text(r325.PARENT_MODEL),
            "sha256": model_digest,
        },
        "analysis": {
            "path": r325._path_text(r325.PARENT_ANALYSIS),
            "sha256": analysis_digest,
        },
        "r325_seal": {"path": _path_text(R325_SEAL), "sha256": r325_seal_digest},
        "r325_execution": {
            "path": _path_text(R325_EXECUTION),
            "sha256": r325_execution_digest,
        },
        "r325_contract_payload_sha256": r325_contract_digest,
        "r325_contract": r325_contract,
    }
    contract = build_contract()
    if (
        seal.get("round") != ROUND_ID
        or seal.get("question") != QUESTION_ID
        or seal.get("contract") != contract
        or seal.get("contract_payload_sha256") != _payload_sha256(contract)
        or seal.get("parent") != expected_parent
        or seal.get("sources") != _sources()
    ):
        raise RuntimeError("R326 seal contract, parent, dependency, or source drift")
    return seal, digest


def _r325_status_map() -> dict[tuple[str, str, str], dict[str, Any]]:
    execution, _digest = r325._read_verified_json(R325_EXECUTION)
    result: dict[tuple[str, str, str], dict[str, Any]] = {}
    for arm in ("retained_cross", "cross_deleted"):
        for row in execution["arms"][arm]["rows"]["development"]:
            result[(arm, row["case"], row["mismatch"])] = row
    if len(result) != 64:
        raise RuntimeError("R325 development status inventory is incomplete")
    return result


class EvaluationTask(NamedTuple):
    index: int
    arm: str
    phase: str
    case: r325.FeedbackCase
    mismatch_name: str
    mismatch: np.ndarray
    include_reference: bool


def _initialize_worker(
    plants: dict[str, Any],
    designs: dict[str, dict[str, Any]],
    r325_status: dict[tuple[str, str, str], dict[str, Any]],
) -> None:
    global _WORKER_PLANTS, _WORKER_DESIGNS, _WORKER_R325_STATUS, _THREAD_LIMITER
    _THREAD_LIMITER = threadpool_limits(limits=1)
    _WORKER_PLANTS = plants
    _WORKER_DESIGNS = designs
    _WORKER_R325_STATUS = r325_status


def _failure_step(message: object) -> int | None:
    match = re.search(r"step (\d+)", str(message))
    return None if match is None else int(match.group(1))


def _legacy_prefix(
    plant: Any,
    design: Any,
    case: r325.FeedbackCase,
    mismatch: np.ndarray,
    expected: dict[str, Any],
) -> dict[str, Any]:
    limits = FeedbackLimits()
    disturbances = np.asarray(case.disturbance, dtype=float)
    state_matrix = np.asarray(plant.state_matrix, dtype=float)
    input_matrix = np.asarray(plant.input_matrix, dtype=float)
    output_matrix = np.asarray(plant.output_matrix, dtype=float)
    feedthrough = np.asarray(plant.feedthrough_matrix, dtype=float)
    state = np.zeros(state_matrix.shape[0])
    estimate_prediction = np.zeros(design.augmented_model.state_matrix.shape[0])
    previous_output = np.zeros(4)
    previous_node_action = np.zeros(4)
    current_soc = np.broadcast_to(np.asarray(case.initial_soc, dtype=float), (4,)).copy()
    prediction_free, prediction_forced = _prediction_matrices(
        design.augmented_model, design.horizon_steps
    )
    samples: list[dict[str, object]] = []
    failure_message: str | None = None
    failure_kind: str | None = None
    expected_failure_step = _failure_step(expected.get("error"))
    target_steps = (
        expected_failure_step if expected.get("solver_failed") is True else disturbances.shape[0]
    )
    if target_steps is None:
        raise RuntimeError("R325 failed row has no registered failure step")
    candidate_solver = SparseConstrainedHorizonSolver(design, limits)
    candidate_solver.reset()
    for step, disturbance in enumerate(disturbances[:target_steps]):
        innovation = (
            previous_output - design.augmented_model.measurement_matrix @ estimate_prediction
        )
        corrected_estimate = estimate_prediction + design.filter_gain @ innovation
        try:
            solution = solve_constrained_horizon_action(
                design,
                corrected_estimate=corrected_estimate,
                previous_node_action=previous_node_action,
                soc=current_soc,
                limits=limits,
            )
        except (RuntimeError, ValueError) as exc:
            failure_kind = "execution_error"
            failure_message = str(exc)
            break
        if not solution.feasible:
            failure_kind = "solver_failed"
            failure_message = f"step {step} finite-horizon solve failed: {solution.message}"
            break
        reference_predicted_outputs = (
            prediction_free @ corrected_estimate
            + prediction_forced @ solution.predicted_coordinate_actions.reshape(-1)
        ).reshape(design.horizon_steps, 4)
        candidate = candidate_solver.solve(
            corrected_estimate=corrected_estimate,
            previous_node_action=previous_node_action,
            soc=current_soc,
            warm_start=True,
        )
        if not candidate.solution.feasible:
            failure_kind = "candidate_reference_failed"
            failure_message = (
                f"step {step} same-input candidate failed: {candidate.solution.message}"
            )
            break
        samples.append(
            {
                "step": step,
                "node_action_max_abs_error": float(
                    np.max(
                        np.abs(
                            solution.predicted_node_actions
                            - candidate.solution.predicted_node_actions
                        )
                    )
                ),
                "coordinate_action_max_abs_error": float(
                    np.max(
                        np.abs(
                            solution.predicted_coordinate_actions
                            - candidate.solution.predicted_coordinate_actions
                        )
                    )
                ),
                "predicted_output_max_abs_error": float(
                    np.max(np.abs(reference_predicted_outputs - candidate.predicted_outputs))
                ),
            }
        )
        coordinate_action = solution.coordinate_action
        node_action = solution.node_action
        total_input = disturbance + coordinate_action
        model_output = output_matrix @ state + feedthrough @ total_input
        output = model_output + mismatch @ model_output
        state = state_matrix @ state + input_matrix @ total_input
        current_soc = _advance_soc(current_soc, node_action, limits)
        estimate_prediction = (
            design.augmented_model.state_matrix @ corrected_estimate
            + design.augmented_model.input_matrix @ coordinate_action
        )
        previous_output = output
        previous_node_action = node_action
    return {
        "samples": samples,
        "target_steps": target_steps,
        "replay_complete": bool(failure_kind is None and len(samples) == target_steps),
        "failure_kind": failure_kind,
        "failure_message": failure_message,
        "failure_step": _failure_step(failure_message),
    }


def _evaluate_one(
    task: EvaluationTask,
    plants: dict[str, Any],
    designs: dict[str, dict[str, Any]],
    r325_status: dict[tuple[str, str, str], dict[str, Any]],
) -> dict[str, Any]:
    plant = plants[task.case.point]
    design = designs[task.arm][task.case.point]
    zero_energy = r325._zero_energy(plant, task.case, task.mismatch)
    row: dict[str, Any] = {
        "arm": task.arm,
        "phase": task.phase,
        "case": task.case.name,
        "mismatch": task.mismatch_name,
        "zero_output_energy": zero_energy,
    }
    legacy = None
    if task.include_reference:
        expected = r325_status[(task.arm, task.case.name, task.mismatch_name)]
        legacy = _legacy_prefix(plant, design, task.case, task.mismatch, expected)
        row.update(
            {
                "reference_completed_steps": len(legacy["samples"]),
                "reference_target_steps": legacy["target_steps"],
                "reference_failure_kind": legacy["failure_kind"],
                "reference_failure_step": legacy["failure_step"],
                "reference_failure_message": legacy["failure_message"],
                "reference_status_matches_r325": legacy["replay_complete"],
                "prefix_samples": legacy["samples"],
            }
        )
    try:
        trace = simulate_sparse_constrained_horizon_feedback(
            plant,
            task.case.disturbance,
            design=design,
            initial_soc=task.case.initial_soc,
            mismatch_transform=task.mismatch,
        )
        if zero_energy <= np.finfo(float).tiny:
            raise RuntimeError("zero-control output energy is degenerate")
        ramp = np.vstack((trace.base.node_actions[:1], np.diff(trace.base.node_actions, axis=0)))
        row.update(
            {
                "solver_failed": False,
                "execution_error": False,
                "output_energy": trace.base.output_energy,
                "output_energy_ratio": float(trace.base.output_energy / zero_energy),
                "coordinate_action_energy": trace.base.coordinate_action_energy,
                "maximum_node_power": float(np.max(np.abs(trace.base.node_actions))),
                "maximum_node_ramp": float(np.max(np.abs(ramp))),
                "minimum_soc": float(np.min(trace.base.soc)),
                "maximum_soc": float(np.max(trace.base.soc)),
                "maximum_solver_iterations": int(np.max(trace.base.solver_iterations)),
                "maximum_constraint_residual": trace.base.maximum_constraint_residual,
                "constraint_violation_count": trace.base.constraint_violation_count,
                "maximum_primal_residual": trace.maximum_primal_residual,
                "maximum_dual_residual": trace.maximum_dual_residual,
                "maximum_primal_residual_ratio": (trace.maximum_primal_residual_ratio),
                "maximum_dual_residual_ratio": trace.maximum_dual_residual_ratio,
            }
        )
    except ConstrainedHorizonInfeasible as exc:
        row.update(
            {
                "solver_failed": True,
                "execution_error": False,
                "error": str(exc),
                "prefix_samples": [],
            }
        )
    except (RuntimeError, ValueError) as exc:
        row.update(
            {
                "solver_failed": False,
                "execution_error": True,
                "error": str(exc),
                "prefix_samples": [],
            }
        )
    return row


def _evaluate_task(task: EvaluationTask) -> tuple[int, dict[str, Any]]:
    if _WORKER_PLANTS is None or _WORKER_DESIGNS is None or _WORKER_R325_STATUS is None:
        raise RuntimeError("R326 worker was not initialized")
    return (
        task.index,
        _evaluate_one(
            task,
            _WORKER_PLANTS,
            _WORKER_DESIGNS,
            _WORKER_R325_STATUS,
        ),
    )


def _evaluate_phase(
    phase: str,
    plants: dict[str, Any],
    designs: dict[str, dict[str, Any]],
    cases: list[r325.FeedbackCase],
    transforms: dict[str, np.ndarray],
    *,
    include_reference: bool,
    maximum_workers: int,
) -> dict[str, list[dict[str, Any]]]:
    status = _r325_status_map()
    tasks: list[EvaluationTask] = []
    for arm in ("retained_cross", "cross_deleted"):
        for case in cases:
            for mismatch_name, mismatch in transforms.items():
                tasks.append(
                    EvaluationTask(
                        index=len(tasks),
                        arm=arm,
                        phase=phase,
                        case=case,
                        mismatch_name=mismatch_name,
                        mismatch=mismatch,
                        include_reference=include_reference,
                    )
                )
    if maximum_workers == 1:
        indexed = [(task.index, _evaluate_one(task, plants, designs, status)) for task in tasks]
    else:
        with ProcessPoolExecutor(
            max_workers=maximum_workers,
            mp_context=mp.get_context("spawn"),
            initializer=_initialize_worker,
            initargs=(plants, designs, status),
        ) as pool:
            indexed = list(pool.map(_evaluate_task, tasks, chunksize=1))
    indexed.sort(key=lambda item: item[0])
    rows = {"retained_cross": [], "cross_deleted": []}
    for _index, row in indexed:
        rows[row["arm"]].append(row)
    return rows


def _execution_models_and_designs() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    parent, _model_digest, _analysis, _analysis_digest = r325._load_parent()
    retained, markov = r325._models(parent)
    synthesis_models = {
        "retained_cross": retained,
        "cross_deleted": r325._cross_deleted_models(markov),
    }
    designs: dict[str, dict[str, Any]] = {}
    for arm, models in synthesis_models.items():
        arm_designs, feasible, error = r325._designs(models)
        if not feasible:
            raise RuntimeError(f"{arm} observer synthesis failed: {error}")
        designs[arm] = arm_designs
    return retained, designs


def _design_summary(designs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for arm, arm_designs in designs.items():
        result[arm] = {}
        for point, design in arm_designs.items():
            solver = SparseConstrainedHorizonSolver(design)
            result[arm][point] = {
                "minimum_action_hessian_eigenvalue": (solver.minimum_action_hessian_eigenvalue),
                "action_optimum_is_unique": solver.action_optimum_is_unique,
            }
    return result


def _development_payload(
    seal: dict[str, Any], seal_digest: str, *, created_utc: str
) -> dict[str, Any]:
    plants, designs = _execution_models_and_designs()
    rows = _evaluate_phase(
        "development",
        plants,
        designs,
        r325.development_cases(),
        {"nominal": np.zeros((4, 4))},
        include_reference=True,
        maximum_workers=int(seal["contract"]["solver_repair"]["development_workers"]),
    )
    arms = {
        arm: {
            "observer_synthesis_succeeded": True,
            "observer_synthesis_error": None,
            "rows": {"development": rows[arm]},
        }
        for arm in ("retained_cross", "cross_deleted")
    }
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": created_utc,
        "seal_sha256": seal_digest,
        "contract_payload_sha256": seal["contract_payload_sha256"],
        "r325_contract_payload_sha256": seal["contract"]["solver_repair"][
            "r325_contract_payload_sha256"
        ],
        "dependency_fingerprint": dependency_fingerprint(),
        "solver_settings": _solver_contract(),
        "sealed_source_identity": True,
        "r321_analysis_access": "HASH-ONLY-NO-PARSE",
        "holdout_accessed": False,
        "designs": _design_summary(designs),
        "arms": arms,
        "eval": "NOT-APPLICABLE-MODEL-ONLY",
        "physical_execution_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }


def _holdout_rows(seal: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    plants, designs = _execution_models_and_designs()
    return _evaluate_phase(
        "holdout",
        plants,
        designs,
        r325.holdout_cases(),
        r325.mismatch_transforms(),
        include_reference=False,
        maximum_workers=int(seal["contract"]["solver_repair"]["holdout_workers"]),
    )


def execute(seal_path: Path, expected: str, out_dir: Path) -> str:
    seal, seal_digest = _load_seal(seal_path, expected)
    created_utc = datetime.now(UTC).isoformat()
    first = _development_payload(seal, seal_digest, created_utc=created_utc)
    second = _development_payload(seal, seal_digest, created_utc=created_utc)
    replay = _canonical_bytes(first) == _canonical_bytes(second)
    first["deterministic_execution_replay"] = replay
    first["deterministic_development_replay"] = replay
    first["holdout_accessed"] = False
    if solver_development_allows_holdout(first, seal["contract"]):
        first_holdout = _holdout_rows(seal)
        second_holdout = _holdout_rows(seal)
        holdout_replay = _canonical_bytes(first_holdout) == _canonical_bytes(second_holdout)
        first["holdout_accessed"] = True
        first["deterministic_holdout_replay"] = holdout_replay
        first["deterministic_execution_replay"] = bool(replay and holdout_replay)
        for arm in ("retained_cross", "cross_deleted"):
            first["arms"][arm]["rows"]["holdout"] = first_holdout[arm]
    return _write_new_json(out_dir / "execution.json", first)


def analyse(seal_path: Path, expected: str, out_dir: Path) -> dict[str, str]:
    seal, seal_digest = _load_seal(seal_path, expected)
    execution, execution_digest = r325._read_verified_json(out_dir / "execution.json")
    execution_view = dict(execution)
    execution_view["execution_sha256"] = execution_digest
    first = analyse_r326_execution(execution_view, seal["contract"], analysis_replay=True)
    second = analyse_r326_execution(execution_view, seal["contract"], analysis_replay=True)
    deterministic = _canonical_bytes(first) == _canonical_bytes(second)
    if not deterministic:
        first = analyse_r326_execution(execution_view, seal["contract"], analysis_replay=False)
    analysis_digest = _write_new_json(out_dir / "analysis.json", first)
    provenance = {
        "round": ROUND_ID,
        "seal_sha256": seal_digest,
        "execution_sha256": execution_digest,
        "analysis_sha256": analysis_digest,
        "sources": seal["sources"],
        "parent": seal["parent"],
        "dependency_fingerprint": seal["contract"]["solver_repair"]["dependency_fingerprint"],
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
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("prepare", "execute", "analyse"):
        item = subparsers.add_parser(command)
        item.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
        if command != "prepare":
            item.add_argument("--expected-sha256", required=True)
            item.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "prepare":
        print(prepare(args.seal))
    elif args.command == "execute":
        print(execute(args.seal, args.expected_sha256, args.out))
    else:
        print(json.dumps(analyse(args.seal, args.expected_sha256, args.out), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
