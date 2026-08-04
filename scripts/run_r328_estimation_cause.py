"""Prepare, execute, and analyse the R328 retained-state oracle diagnosis."""

from __future__ import annotations

import argparse
import hashlib
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

import scripts.run_r326_solver_adequacy as r326  # noqa: E402
from probes.r328_estimation_cause import (  # noqa: E402
    analyse_r328_estimation_diagnosis,
)

from andes_rl_kundur.control.model_first_constrained_horizon import (  # noqa: E402
    _advance_soc,
)
from andes_rl_kundur.control.model_first_constrained_qp import (  # noqa: E402
    SparseConstrainedHorizonSolver,
)
from andes_rl_kundur.control.model_first_offline_feedback import (  # noqa: E402
    FeedbackLimits,
)

ROUND_ID = "R328"
QUESTION_ID = "Q-0081"
R326_SEAL = ROOT / "memory/rounds/R326/solver_adequacy_seal.json"
R326_EXECUTION = ROOT / "results/r326_solver_adequacy/execution.json"
R327_SEAL = ROOT / "memory/rounds/R327/reference_recovery_seal.json"
R327_EXECUTION = ROOT / "results/r327_reference_recovery/execution.json"
R327_ANALYSIS = ROOT / "results/r327_reference_recovery/analysis.json"
R327_PROVENANCE = ROOT / "results/r327_reference_recovery/provenance.json"
R327_MANIFEST = ROOT / "results/r327_reference_recovery/run_manifest.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R328/estimation_cause_seal.json"
DEFAULT_OUT = ROOT / "results/r328_estimation_cause"
DEVELOPMENT_WORKERS = min(8, os.cpu_count() or 1)

_WORKER_PLANTS: dict[str, Any] | None = None
_WORKER_DESIGNS: dict[str, Any] | None = None
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
    return r326._write_new_json(path, payload)


def _r326_contract() -> dict[str, Any]:
    seal, _digest = r326.r325._read_verified_json(R326_SEAL)
    contract = seal.get("contract")
    if not isinstance(contract, dict) or seal.get("contract_payload_sha256") != _payload_sha256(
        contract
    ):
        raise RuntimeError("R326 sealed contract is invalid")
    return contract


def build_contract() -> dict[str, object]:
    parent = _r326_contract()
    return {
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "model-only-retained-state-estimation-cause",
        "parent_round": "R327",
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
        "estimation_diagnosis": {
            "arm": "retained_cross",
            "single_factor": "observer-estimate-to-exact-augmented-state",
            "exact_state": "retained-plant-state-plus-previous-delivered-output",
            "maximum_constraint_residual": 1.0e-8,
            "maximum_normalized_residual_ratio": 1.0,
            "require_every_case_below_zero_control": True,
            "development_workers": DEVELOPMENT_WORKERS,
            "native_numerical_threads_per_worker": 1,
            "holdout_access": "forbidden",
            "cross_deleted_oracle": "forbidden-nonidentifiable-state-basis",
        },
        "comparison_identifiability": {
            "decision": "ALLOW",
            "estimand": "retained-controller-estimation-layer-loss-on-development-bank",
            "oracle_information": True,
        },
        "classification": [
            "INVALID-ESTIMATION-DIAGNOSIS",
            "ESTIMATION-NOT-DOMINANT",
            "ESTIMATION-LAYER-CAUSE",
        ],
        "eval": "NOT-APPLICABLE-MODEL-ONLY",
        "physical_execution_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R328/plan.md",
        "question": ROOT / "memory/questions/Q-0081.md",
        "r326_seal": R326_SEAL,
        "r326_execution": R326_EXECUTION,
        "r327_seal": R327_SEAL,
        "r327_execution": R327_EXECUTION,
        "r327_analysis": R327_ANALYSIS,
        "r327_provenance": R327_PROVENANCE,
        "r327_manifest": R327_MANIFEST,
        "r327_claim": ROOT / "memory/claims/CLM-0845.md",
        "r327_feed": ROOT / "paper/decoupling_marl_model_first/reports/R327.md",
        "r325_adapter": ROOT / "scripts/run_r325_constrained_horizon.py",
        "r326_adapter": ROOT / "scripts/run_r326_solver_adequacy.py",
        "solver_module": ROOT / "src/andes_rl_kundur/control/model_first_constrained_qp.py",
        "validation_probe": ROOT / "probes/r328_estimation_cause.py",
        "adapter": ROOT / "scripts/run_r328_estimation_cause.py",
        "validation_tests": ROOT / "tests/test_r328_estimation_cause.py",
        "adapter_tests": ROOT / "tests/test_r328_estimation_cause_adapter.py",
        "project_dependencies": ROOT / "pyproject.toml",
        "artifact_io": ROOT / "memory/tools/artifact_io.py",
    }


def _sources() -> dict[str, dict[str, str]]:
    return {
        name: {"path": _path_text(path), "sha256": _sha256_file(path)}
        for name, path in _source_paths().items()
    }


def _parent_bundle() -> tuple[dict[str, Any], dict[str, Any], dict[str, object]]:
    r326_execution, r326_execution_digest = r326.r325._read_verified_json(R326_EXECUTION)
    r327_seal, r327_seal_digest = r326.r325._read_verified_json(R327_SEAL)
    r327_execution, r327_execution_digest = r326.r325._read_verified_json(R327_EXECUTION)
    r327_analysis, r327_analysis_digest = r326.r325._read_verified_json(R327_ANALYSIS)
    _provenance, provenance_digest = r326.r325._read_verified_json(R327_PROVENANCE)
    _manifest, manifest_digest = r326.r325._read_verified_json(R327_MANIFEST)
    retained = r327_analysis.get("arms", {}).get("retained_cross", {}).get("development", {})
    if (
        r327_analysis.get("classification") != "DEVELOPMENT-NO-GO"
        or r327_analysis.get("combined_solver_repair_passed") is not True
        or r327_analysis.get("holdout_accessed") is not False
        or retained.get("valid") is not True
        or retained.get("case_count") != 32
        or r326_execution.get("holdout_accessed") is not False
    ):
        raise RuntimeError("R327 parent is not the exact valid retained development no-go")
    parent = {
        "r326_execution": {
            "path": _path_text(R326_EXECUTION),
            "sha256": r326_execution_digest,
        },
        "r327_seal": {"path": _path_text(R327_SEAL), "sha256": r327_seal_digest},
        "r327_execution": {
            "path": _path_text(R327_EXECUTION),
            "sha256": r327_execution_digest,
        },
        "r327_analysis": {
            "path": _path_text(R327_ANALYSIS),
            "sha256": r327_analysis_digest,
        },
        "r327_provenance": {
            "path": _path_text(R327_PROVENANCE),
            "sha256": provenance_digest,
        },
        "r327_manifest": {
            "path": _path_text(R327_MANIFEST),
            "sha256": manifest_digest,
        },
        "r327_contract_payload_sha256": r327_seal["contract_payload_sha256"],
    }
    return r326_execution, r327_analysis, parent


def prepare(seal_path: Path) -> str:
    _r326_execution, _r327_analysis, parent = _parent_bundle()
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
    seal, digest = r326.r325._read_verified_json(path, expected)
    _r326_execution, _r327_analysis, parent = _parent_bundle()
    contract = build_contract()
    if (
        seal.get("round") != ROUND_ID
        or seal.get("question") != QUESTION_ID
        or seal.get("contract") != contract
        or seal.get("contract_payload_sha256") != _payload_sha256(contract)
        or seal.get("parent") != parent
        or seal.get("sources") != _sources()
    ):
        raise RuntimeError("R328 seal contract, parent, or source drift")
    return seal, digest


def _retained_models_and_designs() -> tuple[dict[str, Any], dict[str, Any]]:
    parent, _model_digest, _analysis, _analysis_digest = r326.r325._load_parent()
    retained, _markov = r326.r325._models(parent)
    designs, feasible, error = r326.r325._designs(retained)
    if not feasible:
        raise RuntimeError(f"retained-cross design synthesis failed: {error}")
    return retained, designs


def _state_coordinate_error(plant: Any, design: Any) -> float:
    augmented = design.augmented_model
    order = plant.state_matrix.shape[0]
    differences = (
        np.asarray(augmented.state_matrix[:order, :order]) - plant.state_matrix,
        np.asarray(augmented.input_matrix[:order]) - plant.input_matrix,
        np.asarray(augmented.regulated_output_matrix[:, :order]) - plant.output_matrix,
        np.asarray(augmented.feedthrough_matrix) - plant.feedthrough_matrix,
    )
    return float(max(np.max(np.abs(item)) for item in differences))


def _exact_augmented_state(state: object, previous_output: object) -> np.ndarray:
    plant_state = np.asarray(state, dtype=float)
    delivered = np.asarray(previous_output, dtype=float)
    if plant_state.ndim != 1 or delivered.shape != (4,):
        raise ValueError("exact state requires one plant-state vector and four outputs")
    return np.concatenate((plant_state, delivered))


class EvaluationTask(NamedTuple):
    index: int
    case: Any


def _initialize_worker(plants: dict[str, Any], designs: dict[str, Any]) -> None:
    global _WORKER_PLANTS, _WORKER_DESIGNS, _THREAD_LIMITER
    _THREAD_LIMITER = threadpool_limits(limits=1)
    _WORKER_PLANTS = plants
    _WORKER_DESIGNS = designs


def _simulate_exact_state_case(plant: Any, design: Any, case: Any) -> dict[str, object]:
    limits = FeedbackLimits()
    disturbances = np.asarray(case.disturbance, dtype=float)
    state_matrix = np.asarray(plant.state_matrix, dtype=float)
    input_matrix = np.asarray(plant.input_matrix, dtype=float)
    output_matrix = np.asarray(plant.output_matrix, dtype=float)
    feedthrough = np.asarray(plant.feedthrough_matrix, dtype=float)
    state = np.zeros(state_matrix.shape[0])
    previous_output = np.zeros(4)
    previous_node_action = np.zeros(4)
    current_soc = np.broadcast_to(np.asarray(case.initial_soc, dtype=float), (4,)).copy()
    solver = SparseConstrainedHorizonSolver(design, limits)
    solver.reset()
    outputs = np.zeros_like(disturbances)
    node_actions = np.zeros_like(disturbances)
    coordinate_actions = np.zeros_like(disturbances)
    soc_history = np.zeros((disturbances.shape[0] + 1, 4))
    soc_history[0] = current_soc
    maximum_residual = 0.0
    maximum_primal_ratio = 0.0
    maximum_dual_ratio = 0.0
    maximum_state_error = 0.0
    maximum_iterations = 0
    try:
        for step, disturbance in enumerate(disturbances):
            exact_state = _exact_augmented_state(state, previous_output)
            maximum_state_error = max(
                maximum_state_error,
                float(np.max(np.abs(exact_state[: state.size] - state))),
                float(np.max(np.abs(exact_state[state.size :] - previous_output))),
            )
            result = solver.solve(
                corrected_estimate=exact_state,
                previous_node_action=previous_node_action,
                soc=current_soc,
                warm_start=True,
            )
            if not result.solution.feasible:
                raise RuntimeError(result.solution.message)
            action = result.solution.coordinate_action
            node_action = result.solution.node_action
            total_input = disturbance + action
            output = output_matrix @ state + feedthrough @ total_input
            state = state_matrix @ state + input_matrix @ total_input
            current_soc = _advance_soc(current_soc, node_action, limits)
            outputs[step] = output
            coordinate_actions[step] = action
            node_actions[step] = node_action
            soc_history[step + 1] = current_soc
            previous_output = output
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
    zero_energy = r326.r325._zero_energy(plant, case, np.zeros((4, 4)))
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
        "exact_state_construction_error": maximum_state_error,
        "constraint_violation_count": violations,
    }


def _evaluate_task(task: EvaluationTask) -> tuple[int, dict[str, object]]:
    if _WORKER_PLANTS is None or _WORKER_DESIGNS is None:
        raise RuntimeError("R328 worker is not initialized")
    case = task.case
    return task.index, _simulate_exact_state_case(
        _WORKER_PLANTS[case.point], _WORKER_DESIGNS[case.point], case
    )


def _development_pass() -> list[dict[str, object]]:
    plants, designs = _retained_models_and_designs()
    tasks = [
        EvaluationTask(index, case) for index, case in enumerate(r326.r325.development_cases())
    ]
    with ProcessPoolExecutor(
        max_workers=DEVELOPMENT_WORKERS,
        mp_context=mp.get_context("spawn"),
        initializer=_initialize_worker,
        initargs=(plants, designs),
    ) as pool:
        indexed = list(pool.map(_evaluate_task, tasks, chunksize=1))
    indexed.sort(key=lambda item: item[0])
    return [row for _index, row in indexed]


def execute(seal_path: Path, expected: str, out_dir: Path) -> str:
    seal, seal_digest = _load_seal(seal_path, expected)
    plants, designs = _retained_models_and_designs()
    state_error = max(_state_coordinate_error(plants[point], designs[point]) for point in plants)
    created_utc = datetime.now(UTC).isoformat()
    first = _development_pass()
    second = _development_pass()
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": created_utc,
        "seal_sha256": seal_digest,
        "contract_payload_sha256": seal["contract_payload_sha256"],
        "parent_execution_sha256": seal["parent"]["r326_execution"]["sha256"],
        "parent_analysis_sha256": seal["parent"]["r327_analysis"]["sha256"],
        "sealed_source_identity": True,
        "parent_identity": True,
        "state_coordinate_identity": state_error == 0.0,
        "maximum_state_coordinate_error": state_error,
        "deterministic_execution_replay": _canonical_bytes(first) == _canonical_bytes(second),
        "holdout_accessed": False,
        "cross_deleted_oracle_accessed": False,
        "rows": first,
        "eval": "NOT-APPLICABLE-MODEL-ONLY",
        "physical_execution_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }
    return _write_new_json(out_dir / "execution.json", payload)


def analyse(seal_path: Path, expected: str, out_dir: Path) -> dict[str, str]:
    seal, seal_digest = _load_seal(seal_path, expected)
    execution, execution_digest = r326.r325._read_verified_json(out_dir / "execution.json")
    _r326_execution, parent_analysis, _parent = _parent_bundle()
    execution_view = dict(execution)
    execution_view["execution_sha256"] = execution_digest
    first = analyse_r328_estimation_diagnosis(
        execution_view, seal["contract"], parent_analysis, analysis_replay=True
    )
    second = analyse_r328_estimation_diagnosis(
        execution_view, seal["contract"], parent_analysis, analysis_replay=True
    )
    deterministic = _canonical_bytes(first) == _canonical_bytes(second)
    if not deterministic:
        first = analyse_r328_estimation_diagnosis(
            execution_view, seal["contract"], parent_analysis, analysis_replay=False
        )
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
