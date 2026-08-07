"""Rehearse, seal, and execute the create-only R357 physical feasibility gate.

Usage::

    python scripts/run_r357_physical_joint_endpoint_feasibility.py rehearsal
    python scripts/run_r357_physical_joint_endpoint_feasibility.py prepare
    python scripts/run_r357_physical_joint_endpoint_feasibility.py analyse \
        --expected-seal-sha256 <sha256>

The adapter rebuilds only the exposed R356 development cases.  It never reads
the residual holdout, launches ANDES, trains a policy, or accepts an alternate
formal output path.  Every persistent result is create-only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"


ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

import cvxopt  # noqa: E402
import numpy as np  # noqa: E402

from probes.r357_physical_joint_endpoint_feasibility import (  # noqa: E402
    ACCEPTANCE_TOLERANCE,
    SOLVER_ABSOLUTE_TOLERANCE,
    SOLVER_FEASIBILITY_TOLERANCE,
    SOLVER_MAXIMUM_ITERATIONS,
    SOLVER_NAME,
    SOLVER_RELATIVE_TOLERANCE,
    classify_physical_joint_endpoint_feasibility,
    solve_physical_joint_endpoint_feasibility,
)
from scripts import run_r356_joint_endpoint_feasibility as parent  # noqa: E402

from andes_rl_kundur.control.model_first_offline_feedback import (  # noqa: E402
    FeedbackLimits,
)
from andes_rl_kundur.control.residual_headroom import (  # noqa: E402
    build_control_response_map,
)


ROUND_ID = "R357"
QUESTION_ID = "Q-0095"
MINIMUM_IMPROVEMENT = 0.02
EXPECTED_CVXOPT_VERSION = "1.3.3"
PLAN = ROOT / "memory/rounds/R357/plan.md"
QUESTION = ROOT / "memory/questions/Q-0095.md"
DEFAULT_REHEARSAL = ROOT / "memory/rounds/R357/rehearsal.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R357/analysis_seal.json"
DEFAULT_OUT = ROOT / "results/r357_physical_joint_endpoint_feasibility"

R356_PATHS = {
    "r356_plan": ROOT / "memory/rounds/R356/plan.md",
    "r356_rehearsal": ROOT / "memory/rounds/R356/rehearsal.json",
    "r356_seal": ROOT / "memory/rounds/R356/analysis_seal.json",
    "r356_attempt": ROOT
    / "results/r356_joint_endpoint_feasibility/analysis_attempt.json",
    "r356_analysis": ROOT / "results/r356_joint_endpoint_feasibility/analysis.json",
    "r356_manifest": ROOT / "results/r356_joint_endpoint_feasibility/manifest.json",
    "r356_verdict": ROOT / "memory/rounds/R356/verdict.md",
    "r356_feed": ROOT / "paper/decoupling_marl_model_first/reports/R356.md",
    "r356_claim": ROOT / "memory/claims/CLM-0930.md",
    "r356_question": ROOT / "memory/questions/Q-0094.md",
}
FROZEN_R356 = {
    "r356_plan": "12fb0ef7467e3b37939461c4faaccb0bb9311f5b41cabf8c3bb9043a8f1d2799",
    "r356_rehearsal": "d015b51e9de6601a05730d36e31f8092d4998368cd1fc0c6d5dd14389f8cc57f",
    "r356_seal": "2fa030a04633fc944128914d55be1f96da61ca115e00f852909be401e7e1a184",
    "r356_attempt": "9dd3126615d52816f301cf6bb8f64eb4603324eb0f84dec2862e925669fe40eb",
    "r356_analysis": "9a4334c4575cd803114e52c4ed2279efe6defa979734b08e3bc28de0e37332b1",
    "r356_manifest": "4cf10f40c52f56861fa122ede3ff91138ed73cec2c555d0885d0b20d3072e71d",
    "r356_verdict": "bb2cc97a79d5efd709552349979930f8741d239255f82aa19c8dc9545226f50d",
    "r356_feed": "d09e38e70ce46d44e20e3215ac07c0db3c6a9e9fd440a48ce18d04e6371ae0f4",
    "r356_claim": "4e27df5b7feb7f2c365a5196cb9f459a4b4b7b69e06869533bc3c703399e2053",
    "r356_question": "749923cbc1f4c3b501b453e0fffa1018c1f00631d5e433eb4bc4ec78eb493ab8",
}


def read_json(path: Path) -> dict[str, Any]:
    return parent.read_json(path)


def build_contract() -> dict[str, Any]:
    """Return the prospectively frozen R357 execution contract."""

    limits = FeedbackLimits()
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "exact-physical-joint-endpoint-feasibility",
        "inventory": {
            "development_cases": 16,
            "r356_relaxed_infeasible_controls": 6,
            "r356_relaxed_optimal_candidates": 10,
            "samples_per_case": 25,
            "holdout_cases_read": 0,
        },
        "target": {
            "minimum_improvement_fraction": MINIMUM_IMPROVEMENT,
            "common_coordinate_measure": "absolute-error-sum",
            "differential_coordinate_measure": "squared-error-sum",
        },
        "physical_constraints": {
            "edge_coordinates": 3,
            "node_power_included": True,
            "node_ramp_included": True,
            "soc_redundancy_required": True,
            "exact_soc_reconstruction_required": True,
            "node_power": limits.node_power,
            "node_ramp": limits.node_ramp,
            "minimum_soc": limits.minimum_soc,
            "maximum_soc": limits.maximum_soc,
        },
        "solver": {
            "name": SOLVER_NAME,
            "version": EXPECTED_CVXOPT_VERSION,
            "absolute_tolerance": SOLVER_ABSOLUTE_TOLERANCE,
            "relative_tolerance": SOLVER_RELATIVE_TOLERANCE,
            "feasibility_tolerance": SOLVER_FEASIBILITY_TOLERANCE,
            "maximum_iterations": SOLVER_MAXIMUM_ITERATIONS,
            "acceptance_tolerance": ACCEPTANCE_TOLERANCE,
        },
        "execution": {
            "worker_processes": 1,
            "native_threads_per_process": 1,
            "wsl_python_processes": 0,
            "serial": True,
            "create_only": True,
            "retry_authorized": False,
        },
        "decision": {
            "any_accepted_optimal": "PHYSICAL-HEADROOM-FOUND",
            "all_accepted_infeasible": "NO-PHYSICAL-HEADROOM",
            "invalid": "ANALYSIS-INVALID",
        },
        "authorizations": {
            "holdout_authorized": False,
            "training_authorized": False,
            "simulation_authorized": False,
            "andes_authorized": False,
            "distributed_runtime_authorized": False,
            "eval_authorized": False,
        },
    }


def source_paths(*, include_rehearsal: bool) -> dict[str, Path]:
    """Return the complete R357 implementation closure."""

    paths = {
        "plan": PLAN,
        "question": QUESTION,
        "adapter": Path(__file__).resolve(),
        "probe": ROOT / "probes/r357_physical_joint_endpoint_feasibility.py",
        "probe_tests": ROOT
        / "tests/test_r357_physical_joint_endpoint_feasibility.py",
        "adapter_tests": ROOT
        / "tests/test_r357_physical_joint_endpoint_analysis.py",
        "r356_adapter": Path(parent.__file__).resolve(),
        "r356_probe": ROOT / "probes/r356_joint_endpoint_feasibility.py",
        "r353_adapter": ROOT / "scripts/run_r353_matched_residual_headroom.py",
        "r353_probe": ROOT / "probes/r353_matched_residual_headroom.py",
    }
    package_root = ROOT / "src/andes_rl_kundur"
    for path in sorted(package_root.rglob("*.py")):
        relative = path.relative_to(package_root).as_posix()
        paths[f"package_{relative}"] = path
    if include_rehearsal:
        paths["rehearsal"] = DEFAULT_REHEARSAL
    return paths


def parent_paths() -> dict[str, Path]:
    """Return R356 and the inherited development-only parent closure."""

    paths = dict(R356_PATHS)
    paths.update(parent.parent_paths())
    return paths


def source_record(path: Path) -> dict[str, str]:
    return parent.source_record(path)


def source_snapshot(
    *, include_rehearsal: bool, rehearsal_path: Path = DEFAULT_REHEARSAL
) -> dict[str, dict[str, str]]:
    paths = source_paths(include_rehearsal=False)
    if include_rehearsal:
        paths["rehearsal"] = rehearsal_path
    return {name: source_record(path) for name, path in paths.items()}


def parent_snapshot() -> dict[str, dict[str, str]]:
    return {name: source_record(path) for name, path in parent_paths().items()}


def build_development_cases() -> list[dict[str, Any]]:
    return parent.build_development_cases()


def case_identity(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return parent.case_identity(cases)


def r356_status_partition() -> dict[str, list[str]]:
    analysis = read_json(R356_PATHS["r356_analysis"])
    partition = {"primal_infeasible": [], "optimal": []}
    for row in analysis.get("development_results", []):
        status_key = str(row.get("status", "")).replace(" ", "_")
        if row.get("accepted") is not True or status_key not in partition:
            raise RuntimeError("R357 parent contains an unaccepted R356 status")
        partition[status_key].append(str(row["scenario_id"]))
    return partition


def soc_redundancy_diagnostics(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compute the frozen worst-path proof without solving a real endpoint case."""

    limits = FeedbackLimits()
    efficiency_factor = max(
        limits.charge_efficiency,
        1.0 / limits.discharge_efficiency,
    )
    rows: list[dict[str, Any]] = []
    for case in cases:
        initial = np.asarray(case["initial_soc"], dtype=float)
        steps = int(np.asarray(case["base_outputs"]).shape[0])
        maximum_change = float(
            steps
            * limits.sample_period_seconds
            * limits.system_mva
            * limits.node_power
            * efficiency_factor
            / (3600.0 * limits.energy_mwh)
        )
        minimum_margin = float(
            min(
                np.min(initial - limits.minimum_soc),
                np.min(limits.maximum_soc - initial),
            )
        )
        rows.append(
            {
                "scenario_id": str(case["scenario_id"]),
                "steps": steps,
                "maximum_soc_change_bound": maximum_change,
                "minimum_soc_margin": minimum_margin,
                "redundancy_proved": minimum_margin + ACCEPTANCE_TOLERANCE
                >= maximum_change,
            }
        )
    return rows


def synthetic_solver_smoke() -> dict[str, dict[str, Any]]:
    """Exercise feasible, endpoint-infeasible, and physical-infeasible exits."""

    limits = FeedbackLimits()
    outputs = np.asarray([[1.0, 1.0, 0.0, 0.0]])
    zero_commands = np.zeros((1, 4))
    response = np.zeros((4, 3))
    response[0, 0] = -1.0 / limits.node_ramp
    response[1, 0] = -1.0 / limits.node_ramp
    response[2, 0] = 1.0 / limits.node_ramp
    common = {
        "base_outputs": outputs,
        "previous_node_command": np.zeros(4),
        "initial_soc": np.full(4, 0.5),
        "minimum_improvement_fraction": MINIMUM_IMPROVEMENT,
        "limits": limits,
    }
    feasible = solve_physical_joint_endpoint_feasibility(
        **common,
        base_node_commands=zero_commands,
        response_map=response,
    )
    endpoint_infeasible = solve_physical_joint_endpoint_feasibility(
        **common,
        base_node_commands=zero_commands,
        response_map=np.zeros((4, 3)),
    )
    saturated = np.asarray([[limits.node_power, 0.0, 0.0, 0.0]])
    physical_infeasible = solve_physical_joint_endpoint_feasibility(
        **{
            **common,
            "previous_node_command": saturated[0],
        },
        base_node_commands=saturated,
        response_map=response,
    )
    return {
        "feasible": feasible,
        "endpoint_infeasible": endpoint_infeasible,
        "physical_infeasible": physical_infeasible,
    }


def verify_frozen_inputs() -> list[dict[str, Any]]:
    """Verify the terminal R356 decision and exact development identity."""

    for name, path in R356_PATHS.items():
        if not path.is_file() or parent.sha256_file(path) != FROZEN_R356[name]:
            raise RuntimeError(f"R357 frozen R356 input drift: {path}")
    for name in ("r356_rehearsal", "r356_seal", "r356_attempt", "r356_analysis", "r356_manifest"):
        parent.verify_sidecar(R356_PATHS[name])
    analysis = read_json(R356_PATHS["r356_analysis"])
    if (
        analysis.get("round") != "R356"
        or analysis.get("question") != "Q-0094"
        or analysis.get("classification") != "NO-TRAINING"
        or analysis.get("accepted_primal_infeasible_count") != 6
        or analysis.get("accepted_optimal_count") != 10
        or analysis.get("holdout_cases_read") != 0
        or analysis.get("physical_constraints_included") is not False
        or analysis.get("training_authorized") is not False
        or analysis.get("andes_executed") is not False
    ):
        raise RuntimeError("R357 terminal R356 identity drift")
    cases = build_development_cases()
    if case_identity(cases) != analysis.get("development_case_identity"):
        raise RuntimeError("R357 development case identity drift")
    partition = r356_status_partition()
    if len(partition["primal_infeasible"]) != 6 or len(partition["optimal"]) != 10:
        raise RuntimeError("R357 R356 status partition drift")
    soc_rows = soc_redundancy_diagnostics(cases)
    if not soc_rows or any(row["redundancy_proved"] is not True for row in soc_rows):
        raise RuntimeError("R357 state-of-charge redundancy proof failed")
    return cases


def verify_entry_preconditions(out_dir: Path = DEFAULT_OUT) -> list[dict[str, Any]]:
    if out_dir.exists():
        raise FileExistsError(f"R357 result root already exists: {out_dir}")
    if "state: active" not in PLAN.read_text(encoding="utf-8"):
        raise RuntimeError("R357 active plan identity is missing")
    question_text = QUESTION.read_text(encoding="utf-8")
    if "status: in-flight" not in question_text or "opened_round: R357" not in question_text:
        raise RuntimeError("R357 in-flight question identity is missing")
    for path in source_paths(include_rehearsal=False).values():
        if not path.is_file():
            raise RuntimeError(f"R357 source is missing: {path}")
    if cvxopt.__version__ != EXPECTED_CVXOPT_VERSION:
        raise RuntimeError(f"R357 CVXOPT version drift: {cvxopt.__version__}")
    cases = verify_frozen_inputs()
    if len(cases) != 16:
        raise RuntimeError("R357 requires exactly sixteen development cases")
    return cases


def rehearsal(record_path: Path = DEFAULT_REHEARSAL) -> str:
    """Exercise the formal pre-attempt path without solving the real bank."""

    if record_path.exists():
        raise FileExistsError(f"create-only output already exists: {record_path}")
    cases = verify_entry_preconditions()
    smoke = synthetic_solver_smoke()
    if not (
        smoke["feasible"].get("status") == "optimal"
        and smoke["feasible"].get("accepted") is True
        and smoke["endpoint_infeasible"].get("status") == "primal infeasible"
        and smoke["endpoint_infeasible"].get("accepted") is True
        and smoke["physical_infeasible"].get("status") == "primal infeasible"
        and smoke["physical_infeasible"].get("accepted") is True
    ):
        raise RuntimeError("R357 synthetic solver smoke failed")
    contract = build_contract()
    return parent.write_new_json(
        record_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract_payload_sha256": parent.payload_sha256(contract),
            "development_case_identity": case_identity(cases),
            "development_case_count": len(cases),
            "r356_status_partition": r356_status_partition(),
            "soc_redundancy_diagnostics": soc_redundancy_diagnostics(cases),
            "holdout_cases_read": 0,
            "synthetic_solver_smoke": smoke,
            "source_snapshot": source_snapshot(include_rehearsal=False),
            "parent_snapshot": parent_snapshot(),
            "formal_output_absent": True,
            "attempt_created": False,
            "result_created": False,
            "andes_executed": False,
            "training_executed": False,
        },
    )


def prepare(
    seal_path: Path = DEFAULT_SEAL,
    *,
    rehearsal_path: Path = DEFAULT_REHEARSAL,
) -> str:
    """Create the source-, parent-, identity-, and rehearsal-bound seal."""

    if seal_path.exists():
        raise FileExistsError(f"create-only output already exists: {seal_path}")
    cases = verify_entry_preconditions()
    parent.verify_sidecar(rehearsal_path)
    record = read_json(rehearsal_path)
    contract = build_contract()
    sources = source_snapshot(include_rehearsal=False)
    parents = parent_snapshot()
    if (
        record.get("round") != ROUND_ID
        or record.get("question") != QUESTION_ID
        or record.get("contract_payload_sha256") != parent.payload_sha256(contract)
        or record.get("development_case_identity") != case_identity(cases)
        or record.get("r356_status_partition") != r356_status_partition()
        or record.get("soc_redundancy_diagnostics")
        != soc_redundancy_diagnostics(cases)
        or record.get("holdout_cases_read") != 0
        or record.get("synthetic_solver_smoke") != synthetic_solver_smoke()
        or record.get("source_snapshot") != sources
        or record.get("parent_snapshot") != parents
        or record.get("formal_output_absent") is not True
        or record.get("attempt_created") is not False
    ):
        raise RuntimeError("R357 rehearsal record drift")
    return parent.write_new_json(
        seal_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract": contract,
            "contract_payload_sha256": parent.payload_sha256(contract),
            "development_case_identity": case_identity(cases),
            "r356_status_partition": r356_status_partition(),
            "soc_redundancy_diagnostics": soc_redundancy_diagnostics(cases),
            "sources": source_snapshot(
                include_rehearsal=True,
                rehearsal_path=rehearsal_path,
            ),
            "parents": parents,
            "result_root_absent_at_freeze": True,
            "retry_authorized": False,
        },
    )


def load_seal(path: Path, expected_sha256: str) -> tuple[dict[str, Any], str]:
    """Verify the exact R357 seal and complete closure."""

    payload = read_json(path)
    actual = parent.sha256_file(path)
    if actual != expected_sha256:
        raise RuntimeError(f"R357 seal digest mismatch: {actual}")
    parent.verify_sidecar(path)
    cases = verify_entry_preconditions()
    contract = payload.get("contract")
    if (
        payload.get("round") != ROUND_ID
        or payload.get("question") != QUESTION_ID
        or contract != build_contract()
        or payload.get("contract_payload_sha256") != parent.payload_sha256(contract)
        or payload.get("development_case_identity") != case_identity(cases)
        or payload.get("r356_status_partition") != r356_status_partition()
        or payload.get("soc_redundancy_diagnostics")
        != soc_redundancy_diagnostics(cases)
        or payload.get("sources") != source_snapshot(include_rehearsal=True)
        or payload.get("parents") != parent_snapshot()
        or payload.get("retry_authorized") is not False
    ):
        raise RuntimeError("R357 contract, identity, source, or parent drift")
    return payload, actual


def analyse(expected_sha256: str) -> str:
    """Execute the single sealed serial physical-feasibility analysis."""

    seal, seal_digest = load_seal(DEFAULT_SEAL, expected_sha256)
    DEFAULT_OUT.mkdir(parents=True, exist_ok=False)
    attempt_path = DEFAULT_OUT / "analysis_attempt.json"
    attempt_digest = parent.write_new_json(
        attempt_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "worker_processes": 1,
            "native_threads_per_process": 1,
            "wsl_python_processes": 0,
            "retry_authorized": False,
            "holdout_cases_read": 0,
            "andes_executed": False,
            "training_executed": False,
        },
    )
    started = time.perf_counter()
    try:
        cases = build_development_cases()
        if case_identity(cases) != seal["development_case_identity"]:
            raise RuntimeError("R357 formal case identity drift")
        rows: list[dict[str, Any]] = []
        limits = FeedbackLimits()
        for case in cases:
            outputs = np.asarray(case["base_outputs"], dtype=float)
            response = build_control_response_map(
                case["model"], horizon=int(outputs.shape[0])
            )
            result = solve_physical_joint_endpoint_feasibility(
                base_outputs=outputs,
                base_node_commands=case["base_node_commands"],
                previous_node_command=case["previous_node_command"],
                initial_soc=case["initial_soc"],
                response_map=response,
                minimum_improvement_fraction=MINIMUM_IMPROVEMENT,
                limits=limits,
            )
            rows.append(
                {
                    "scenario_id": case["scenario_id"],
                    "point": case["point"],
                    "channel": case["channel"],
                    "sign": case["sign"],
                    **result,
                }
            )
        decision = classify_physical_joint_endpoint_feasibility(rows)
        analysis_path = DEFAULT_OUT / "analysis.json"
        analysis_digest = parent.write_new_json(
            analysis_path,
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "created_utc": datetime.now(UTC).isoformat(),
                "seal_sha256": seal_digest,
                "contract_payload_sha256": seal["contract_payload_sha256"],
                "analysis_attempt_sha256": attempt_digest,
                "elapsed_seconds": time.perf_counter() - started,
                "development_case_identity": case_identity(cases),
                "r356_status_partition": seal["r356_status_partition"],
                "soc_redundancy_diagnostics": seal["soc_redundancy_diagnostics"],
                "development_results": rows,
                **decision,
                "holdout_case_identity": [],
                "holdout_cases_read": 0,
                "minimum_improvement_fraction": MINIMUM_IMPROVEMENT,
                "physical_constraints_included": True,
                "information_constraints_included": False,
                "target_changed": False,
                "andes_executed": False,
                "physical_trajectory_created": False,
                "distributed_runtime_executed": False,
                "eval_executed": False,
            },
        )
        manifest_digest = parent.write_new_json(
            DEFAULT_OUT / "manifest.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "entries": [
                    {
                        "path": attempt_path.relative_to(ROOT).as_posix(),
                        "sha256": attempt_digest,
                    },
                    {
                        "path": analysis_path.relative_to(ROOT).as_posix(),
                        "sha256": analysis_digest,
                    },
                ],
            },
        )
        print(f"classification={decision['classification']}", flush=True)
        print(f"analysis_sha256={analysis_digest}", flush=True)
        print(f"manifest_sha256={manifest_digest}", flush=True)
        return analysis_digest
    except Exception as error:
        failure_path = DEFAULT_OUT / "failure.json"
        if not failure_path.exists():
            parent.write_new_json(
                failure_path,
                {
                    "schema_version": 1,
                    "round": ROUND_ID,
                    "question": QUESTION_ID,
                    "classification": "ANALYSIS-INVALID",
                    "created_utc": datetime.now(UTC).isoformat(),
                    "seal_sha256": seal_digest,
                    "analysis_attempt_sha256": attempt_digest,
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "retry_authorized": False,
                    "holdout_cases_read": 0,
                    "training_authorized": False,
                    "simulation_authorized": False,
                },
            )
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    rehearsal_parser = subparsers.add_parser("rehearsal")
    rehearsal_parser.add_argument("--record", type=Path, default=DEFAULT_REHEARSAL)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    analyse_parser = subparsers.add_parser("analyse")
    analyse_parser.add_argument("--expected-seal-sha256", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "rehearsal":
        print(rehearsal(args.record), flush=True)
        return 0
    if args.command == "prepare":
        print(prepare(args.seal), flush=True)
        return 0
    if args.command == "analyse":
        analyse(args.expected_seal_sha256)
        return 0
    raise RuntimeError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
