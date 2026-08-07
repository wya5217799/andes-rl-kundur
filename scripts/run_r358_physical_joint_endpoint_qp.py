"""Prepare and execute the create-only R358 quadratic recovery gate.

Usage::

    python scripts/run_r358_physical_joint_endpoint_qp.py rehearsal
    python scripts/run_r358_physical_joint_endpoint_qp.py prepare
    python scripts/run_r358_physical_joint_endpoint_qp.py analyse \
        --expected-seal-sha256 <sha256>

The adapter reads only the exposed R356 development bank, inherits its six
relaxed infeasibility decisions, and solves the ten relaxed-optimal candidates.
Any source drift, numerical ambiguity, or persistent-output collision fails
closed; retry, holdout access, simulation, and training are unavailable.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cvxopt
import numpy as np

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

from probes.physical_joint_endpoint_qp import (  # noqa: E402
    ACCEPTANCE_TOLERANCE,
    SOLVER_ABSOLUTE_TOLERANCE,
    SOLVER_FEASIBILITY_TOLERANCE,
    SOLVER_MAXIMUM_ITERATIONS,
    SOLVER_NAME,
    SOLVER_RELATIVE_TOLERANCE,
    solve_physical_joint_endpoint_qp,
)
from scripts import run_r357_physical_joint_endpoint_feasibility as predecessor  # noqa: E402

from andes_rl_kundur.control.model_first_offline_feedback import (  # noqa: E402
    FeedbackLimits,
)
from andes_rl_kundur.control.residual_headroom import (  # noqa: E402
    build_control_response_map,
)

ROUND_ID = "R358"
QUESTION_ID = "Q-0095"
MINIMUM_IMPROVEMENT = 0.02
EXPECTED_CVXOPT_VERSION = "1.3.3"
PLAN = ROOT / "memory/rounds/R358/plan.md"
QUESTION = ROOT / "memory/questions/Q-0095.md"
DEFAULT_REHEARSAL = ROOT / "memory/rounds/R358/rehearsal.json"
DEFAULT_SEAL = ROOT / "memory/rounds/R358/analysis_seal.json"
DEFAULT_OUT = ROOT / "results/r358_physical_joint_endpoint_qp"

R357_PATHS = {
    "r357_plan": ROOT / "memory/rounds/R357/plan.md",
    "r357_rehearsal": ROOT / "memory/rounds/R357/rehearsal.json",
    "r357_seal": ROOT / "memory/rounds/R357/analysis_seal.json",
    "r357_attempt": ROOT / "results/r357_physical_joint_endpoint_feasibility/analysis_attempt.json",
    "r357_failure": ROOT / "results/r357_physical_joint_endpoint_feasibility/failure.json",
    "r357_verdict": ROOT / "memory/rounds/R357/verdict.md",
    "r357_feed": ROOT / "paper/decoupling_marl_model_first/reports/R357.md",
    "r357_claim": ROOT / "memory/claims/CLM-0935.md",
}
FROZEN_R357 = {
    "r357_plan": "c099f45e2f7d6417d016c8196e8cb2ecae2e8b38699624cd674d83eb95474573",
    "r357_rehearsal": "ca4bcc0ecb2a94dfb01ccfd8777f186d6a6e844072df88e5ab8b53c8960aa0c7",
    "r357_seal": "26b8babc695e1bec92818d8e9d2fec8b1cc10edbbc65bbce1982cc36060d758c",
    "r357_attempt": "58889a70073253ee39c395b1dfcacc6eb80c9a4a563607a7b8a83ac1e1d0a5ad",
    "r357_failure": "933ea85ca6b753fe1bfaf72ab674427d68f1dee8b1acb2911f3a0aeb010a77fb",
    "r357_verdict": "2216ce3a2c481819740ae4a3ecfc773e1037137358de046bfd5ef7b2e92b6f62",
    "r357_feed": "ef21ab205544209687af096977943bce1e1ff8dca315bd22a77373aba52b71ae",
    "r357_claim": "3a121635eae06b296baa5e8995e5015ab932dc68ad7d66d5e59cbdf61e88dbe3",
}


def source_paths(*, include_rehearsal: bool) -> dict[str, Path]:
    """Return the complete R358 implementation closure."""

    paths = {
        "plan": PLAN,
        "question": QUESTION,
        "adapter": Path(__file__).resolve(),
        "probe": ROOT / "probes/physical_joint_endpoint_qp.py",
        "probe_tests": ROOT / "tests/test_physical_joint_endpoint_qp.py",
        "adapter_tests": ROOT / "tests/test_r358_physical_joint_endpoint_qp_analysis.py",
        "r357_adapter": Path(predecessor.__file__).resolve(),
        "r357_probe": ROOT / "probes/r357_physical_joint_endpoint_feasibility.py",
        "r356_adapter": ROOT / "scripts/run_r356_joint_endpoint_feasibility.py",
        "r356_probe": ROOT / "probes/r356_joint_endpoint_feasibility.py",
    }
    package_root = ROOT / "src/andes_rl_kundur"
    for path in sorted(package_root.rglob("*.py")):
        relative = path.relative_to(package_root).as_posix()
        paths[f"package_{relative}"] = path
    if include_rehearsal:
        paths["rehearsal"] = DEFAULT_REHEARSAL
    return paths


def parent_paths() -> dict[str, Path]:
    """Return the frozen R356 decision and invalid R357 attempt closure."""

    paths = dict(predecessor.parent_paths())
    paths.update(R357_PATHS)
    return paths


def source_record(path: Path) -> dict[str, str]:
    return predecessor.source_record(path)


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
    """Rebuild the exact exposed R356 development bank."""

    return predecessor.build_development_cases()


def case_identity(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return predecessor.case_identity(cases)


def r356_status_partition() -> dict[str, list[str]]:
    return predecessor.r356_status_partition()


def verify_frozen_inputs() -> list[dict[str, Any]]:
    """Verify the accepted R356 closure and immutable invalid R357 attempt."""

    for name, path in R357_PATHS.items():
        if not path.is_file() or predecessor.parent.sha256_file(path) != FROZEN_R357[name]:
            raise RuntimeError(f"R358 frozen R357 input drift: {path}")
    for name in ("r357_rehearsal", "r357_seal", "r357_attempt", "r357_failure"):
        predecessor.parent.verify_sidecar(R357_PATHS[name])
    attempt = predecessor.read_json(R357_PATHS["r357_attempt"])
    failure = predecessor.read_json(R357_PATHS["r357_failure"])
    if (
        attempt.get("round") != "R357"
        or attempt.get("holdout_cases_read") != 0
        or attempt.get("andes_executed") is not False
        or attempt.get("training_executed") is not False
        or failure.get("classification") != "ANALYSIS-INVALID"
        or failure.get("error_type") != "ValueError"
        or failure.get("error_message") != "domain error"
        or failure.get("retry_authorized") is not False
        or failure.get("holdout_cases_read") != 0
    ):
        raise RuntimeError("R358 invalid R357 identity drift")
    result_root = R357_PATHS["r357_failure"].parent
    if (result_root / "analysis.json").exists() or (result_root / "manifest.json").exists():
        raise RuntimeError("R358 R357 output inventory drift")
    cases = predecessor.verify_frozen_inputs()
    partition = r356_status_partition()
    if (
        len(cases) != 16
        or len(partition["primal_infeasible"]) != 6
        or len(partition["optimal"]) != 10
    ):
        raise RuntimeError("R358 R356 development partition drift")
    return cases


def synthetic_solver_smoke() -> dict[str, dict[str, Any]]:
    """Exercise verified feasible and dual-lower-bound decisions."""

    limits = FeedbackLimits()
    feasible_response = np.zeros((4, 3))
    feasible_response[0, 0] = -1.0 / limits.node_ramp
    feasible_response[1, 0] = -1.0 / limits.node_ramp
    feasible_response[2, 0] = 1.0 / limits.node_ramp
    fixed_differential_response = np.zeros((4, 3))
    fixed_differential_response[0, 0] = -1.0 / limits.node_ramp
    common = {
        "base_outputs": np.asarray([[1.0, 1.0, 0.0, 0.0]]),
        "base_node_commands": np.zeros((1, 4)),
        "previous_node_command": np.zeros(4),
        "initial_soc": np.full(4, 0.5),
        "minimum_improvement_fraction": MINIMUM_IMPROVEMENT,
        "limits": limits,
    }
    return {
        "feasible": solve_physical_joint_endpoint_qp(
            **common,
            response_map=feasible_response,
        ),
        "target_infeasible": solve_physical_joint_endpoint_qp(
            **common,
            response_map=fixed_differential_response,
        ),
    }


def minimized_r357_regression() -> dict[str, Any]:
    """Run the four-step R357 prefix that deterministically crashed SOCP."""

    case = build_development_cases()[4]
    steps = 4
    outputs = np.asarray(case["base_outputs"], dtype=float)[:steps]
    response = build_control_response_map(case["model"], horizon=25)[: 4 * steps, : 3 * steps]
    return solve_physical_joint_endpoint_qp(
        base_outputs=outputs,
        base_node_commands=np.asarray(case["base_node_commands"], dtype=float)[:steps],
        previous_node_command=case["previous_node_command"],
        initial_soc=case["initial_soc"],
        response_map=response,
        minimum_improvement_fraction=MINIMUM_IMPROVEMENT,
        limits=FeedbackLimits(),
    )


def verify_entry_preconditions(
    out_dir: Path = DEFAULT_OUT,
) -> list[dict[str, Any]]:
    """Verify the active identity and every pre-attempt dependency."""

    if out_dir.exists():
        raise FileExistsError(f"R358 result root already exists: {out_dir}")
    plan_text = PLAN.read_text(encoding="utf-8")
    if "state: active" not in plan_text or ROUND_ID not in plan_text:
        raise RuntimeError("R358 active plan identity is missing")
    question_text = QUESTION.read_text(encoding="utf-8")
    if "status: in-flight" not in question_text or "R358:" not in question_text:
        raise RuntimeError("R358 in-flight question identity is missing")
    for path in source_paths(include_rehearsal=False).values():
        if not path.is_file():
            raise RuntimeError(f"R358 source is missing: {path}")
    if cvxopt.__version__ != EXPECTED_CVXOPT_VERSION:
        raise RuntimeError(f"R358 CVXOPT version drift: {cvxopt.__version__}")
    cases = verify_frozen_inputs()
    if len(cases) != 16:
        raise RuntimeError("R358 requires exactly sixteen development cases")
    return cases


def rehearsal(
    record_path: Path = DEFAULT_REHEARSAL,
    *,
    out_dir: Path = DEFAULT_OUT,
) -> str:
    """Exercise the formal pre-attempt path without solving the full bank."""

    if record_path.exists():
        raise FileExistsError(f"create-only output already exists: {record_path}")
    cases = verify_entry_preconditions(out_dir)
    smoke = synthetic_solver_smoke()
    regression = minimized_r357_regression()
    if not (
        smoke["feasible"].get("status") == "optimal"
        and smoke["feasible"].get("accepted") is True
        and smoke["feasible"].get("target_feasible") is True
        and smoke["target_infeasible"].get("status") == "optimal"
        and smoke["target_infeasible"].get("accepted") is True
        and smoke["target_infeasible"].get("target_feasible") is False
        and regression.get("status") == "optimal"
        and regression.get("accepted") is True
        and regression.get("target_feasible") is True
    ):
        raise RuntimeError("R358 solver rehearsal checks failed")
    contract = build_contract()
    return predecessor.parent.write_new_json(
        record_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract_payload_sha256": predecessor.parent.payload_sha256(contract),
            "development_case_identity": case_identity(cases),
            "development_case_count": len(cases),
            "r356_status_partition": r356_status_partition(),
            "soc_redundancy_diagnostics": predecessor.soc_redundancy_diagnostics(cases),
            "synthetic_solver_smoke": smoke,
            "minimized_r357_regression": regression,
            "complete_candidate_bank_solved": False,
            "holdout_cases_read": 0,
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
    out_dir: Path = DEFAULT_OUT,
) -> str:
    """Create the source-, parent-, identity-, and rehearsal-bound seal."""

    if seal_path.exists():
        raise FileExistsError(f"create-only output already exists: {seal_path}")
    cases = verify_entry_preconditions(out_dir)
    predecessor.parent.verify_sidecar(rehearsal_path)
    record = predecessor.read_json(rehearsal_path)
    contract = build_contract()
    sources = source_snapshot(include_rehearsal=False)
    parents = parent_snapshot()
    smoke = synthetic_solver_smoke()
    regression = minimized_r357_regression()
    soc_rows = predecessor.soc_redundancy_diagnostics(cases)
    if (
        record.get("round") != ROUND_ID
        or record.get("question") != QUESTION_ID
        or record.get("contract_payload_sha256") != predecessor.parent.payload_sha256(contract)
        or record.get("development_case_identity") != case_identity(cases)
        or record.get("r356_status_partition") != r356_status_partition()
        or record.get("soc_redundancy_diagnostics") != soc_rows
        or record.get("synthetic_solver_smoke") != smoke
        or record.get("minimized_r357_regression") != regression
        or record.get("complete_candidate_bank_solved") is not False
        or record.get("holdout_cases_read") != 0
        or record.get("source_snapshot") != sources
        or record.get("parent_snapshot") != parents
        or record.get("formal_output_absent") is not True
        or record.get("attempt_created") is not False
    ):
        raise RuntimeError("R358 rehearsal record drift")
    return predecessor.parent.write_new_json(
        seal_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract": contract,
            "contract_payload_sha256": predecessor.parent.payload_sha256(contract),
            "development_case_identity": case_identity(cases),
            "r356_status_partition": r356_status_partition(),
            "soc_redundancy_diagnostics": soc_rows,
            "synthetic_solver_smoke": smoke,
            "minimized_r357_regression": regression,
            "sources": source_snapshot(
                include_rehearsal=True,
                rehearsal_path=rehearsal_path,
            ),
            "parents": parents,
            "result_root_absent_at_freeze": True,
            "retry_authorized": False,
        },
    )


def classify_candidate_bank(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Classify ten candidate decisions while inheriting six controls."""

    complete = len(rows) == 10
    accepted = complete and all(
        row.get("status") == "optimal"
        and row.get("accepted") is True
        and isinstance(row.get("target_feasible"), bool)
        for row in rows
    )
    feasible_count = sum(row.get("target_feasible") is True for row in rows)
    infeasible_count = sum(row.get("target_feasible") is False for row in rows)
    if not accepted:
        classification = "ANALYSIS-INVALID"
    elif feasible_count > 0:
        classification = "PHYSICAL-HEADROOM-FOUND"
    else:
        classification = "NO-PHYSICAL-HEADROOM"
    return {
        "classification": classification,
        "inherited_relaxed_infeasible_count": 6,
        "accepted_physical_feasible_candidate_count": feasible_count,
        "accepted_physical_infeasible_candidate_count": infeasible_count,
        "training_authorized": False,
        "simulation_authorized": False,
        "holdout_authorized": False,
    }


def load_seal(
    path: Path,
    expected_sha256: str,
    *,
    out_dir: Path = DEFAULT_OUT,
    rehearsal_path: Path = DEFAULT_REHEARSAL,
) -> tuple[dict[str, Any], str]:
    """Verify the exact R358 seal and its complete closure."""

    payload = predecessor.read_json(path)
    actual = predecessor.parent.sha256_file(path)
    if actual != expected_sha256:
        raise RuntimeError(f"R358 seal digest mismatch: {actual}")
    predecessor.parent.verify_sidecar(path)
    cases = verify_entry_preconditions(out_dir)
    contract = payload.get("contract")
    if (
        payload.get("round") != ROUND_ID
        or payload.get("question") != QUESTION_ID
        or contract != build_contract()
        or payload.get("contract_payload_sha256") != predecessor.parent.payload_sha256(contract)
        or payload.get("development_case_identity") != case_identity(cases)
        or payload.get("r356_status_partition") != r356_status_partition()
        or payload.get("soc_redundancy_diagnostics")
        != predecessor.soc_redundancy_diagnostics(cases)
        or payload.get("synthetic_solver_smoke") != synthetic_solver_smoke()
        or payload.get("minimized_r357_regression") != minimized_r357_regression()
        or payload.get("sources")
        != source_snapshot(include_rehearsal=True, rehearsal_path=rehearsal_path)
        or payload.get("parents") != parent_snapshot()
        or payload.get("retry_authorized") is not False
    ):
        raise RuntimeError("R358 contract, identity, source, or parent drift")
    return payload, actual


def candidate_cases(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select exactly the ten R356 relaxed-optimal candidates."""

    candidate_ids = set(r356_status_partition()["optimal"])
    selected = [case for case in cases if str(case["scenario_id"]) in candidate_ids]
    if len(selected) != 10 or {str(case["scenario_id"]) for case in selected} != candidate_ids:
        raise RuntimeError("R358 candidate identity drift")
    return selected


def solve_candidate_bank(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Solve the complete ten-case bank through the registered public seam."""

    rows: list[dict[str, Any]] = []
    limits = FeedbackLimits()
    for case in candidate_cases(cases):
        outputs = np.asarray(case["base_outputs"], dtype=float)
        response = build_control_response_map(case["model"], horizon=int(outputs.shape[0]))
        result = solve_physical_joint_endpoint_qp(
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
    return rows


def analyse(expected_sha256: str) -> str:
    """Execute the single sealed serial quadratic feasibility analysis."""

    seal, seal_digest = load_seal(DEFAULT_SEAL, expected_sha256)
    DEFAULT_OUT.mkdir(parents=True, exist_ok=False)
    attempt_path = DEFAULT_OUT / "analysis_attempt.json"
    attempt_digest = predecessor.parent.write_new_json(
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
            raise RuntimeError("R358 formal case identity drift")
        rows = solve_candidate_bank(cases)
        decision = classify_candidate_bank(rows)
        analysis_path = DEFAULT_OUT / "analysis.json"
        analysis_digest = predecessor.parent.write_new_json(
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
                "inherited_relaxed_infeasible_scenario_ids": seal["r356_status_partition"][
                    "primal_infeasible"
                ],
                "soc_redundancy_diagnostics": seal["soc_redundancy_diagnostics"],
                "candidate_results": rows,
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
        manifest_digest = predecessor.parent.write_new_json(
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
            predecessor.parent.write_new_json(
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


def build_contract() -> dict[str, Any]:
    """Return the prospectively frozen R358 execution contract."""

    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "normalized-quadratic-physical-feasibility-recovery",
        "inventory": {
            "development_cases": 16,
            "inherited_infeasible_controls": 6,
            "quadratic_candidates": 10,
            "samples_per_case": 25,
            "holdout_cases_read": 0,
        },
        "target": {
            "minimum_improvement_fraction": MINIMUM_IMPROVEMENT,
            "common_coordinate_measure": "absolute-error-sum",
            "differential_coordinate_measure": "squared-error-sum",
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
            "any_accepted_feasible_candidate": "PHYSICAL-HEADROOM-FOUND",
            "all_candidates_accepted_infeasible": "NO-PHYSICAL-HEADROOM",
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


def build_parser() -> argparse.ArgumentParser:
    """Return the fixed create-only R358 command surface."""

    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    rehearsal_parser = subparsers.add_parser("rehearsal")
    rehearsal_parser.add_argument("--record", type=Path, default=DEFAULT_REHEARSAL)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    analyse_parser = subparsers.add_parser("analyse")
    analyse_parser.add_argument("--expected-seal-sha256", required=True)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
