"""Rehearse, seal, and execute the R350 smooth convex residual analysis."""

from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
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

from scripts import run_r345_residual_headroom as r345  # noqa: E402
from scripts import run_r347_scale_stable_residual as r347  # noqa: E402
from scripts import run_r349_certified_residual_analysis as r349  # noqa: E402

ROUND_ID = "R350"
QUESTION_ID = "Q-0091"
WORKERS = 16
HOST_PROCESS_BUDGET = 32
WINDOWS_PYTHON_PROCESSES = 17
DEFAULT_SEAL = ROOT / "memory/rounds/R350/analysis_seal.json"
DEFAULT_REHEARSAL = ROOT / "memory/rounds/R350/rehearsal.json"
DEFAULT_OUT = ROOT / "results/r350_smooth_convex_residual"
PLAN = ROOT / "memory/rounds/R350/plan.md"
R349_SEAL = ROOT / "memory/rounds/R349/analysis_seal.json"
R349_ATTEMPT = ROOT / "results/r349_certified_residual_analysis/analysis_attempt.json"
R349_DIAGNOSTIC = ROOT / "results/r349_certified_residual_analysis/oracle_diagnostic.json"
R349_FAILURE = ROOT / "results/r349_certified_residual_analysis/failure.json"
EXPECTED_R349 = {
    R349_SEAL: "bf4a593e7ebbda446726ea45361e10b035582953263e853b3a6bbcfbf65c3af3",
    R349_ATTEMPT: "86871fa45fb1c0f89ba056ac9c45ce1a60e828fb58dc4822edde8702cd4ff414",
    R349_DIAGNOSTIC: "9d96abc57d740090a3fd37f52d128ad7d839b132b59121be662720c1d2aef5ef",
    R349_FAILURE: "ce4b3b4ff43815e0771fe4f9756684ec19445578e40620908194cb0ed37cf2bc",
}


def build_contract() -> dict[str, Any]:
    """Return the prospectively frozen R350 contract."""

    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "create-only-smooth-convex-residual-headroom",
        "parent_scientific_contract_payload_sha256": r347.PARENT_CONTRACT_SHA256,
        "numerical_repair": {
            "formulation": "smooth-epigraph-endpoint-only-convex-superset",
            "starts": ["feasibility", "zero", "r348"],
            "solver": "SLSQP-with-analytic-jacobians",
            "maximum_iterations": r345.MAXIMUM_ITERATIONS,
            "function_tolerance": r345.FUNCTION_TOLERANCE,
            "feasibility_tolerance_original_units": r345.FEASIBILITY_TOLERANCE,
            "objective_positive_scale": "one-over-sqrt-feasibility-tolerance",
            "active_and_optimality_tolerance": float(
                r345.FEASIBILITY_TOLERANCE**0.5
            ),
            "certificate": "analytic-smooth-epigraph-kkt-nnls",
            "selection": "minimum-physical-edge-norm-then-start-order",
            "physical_limits": "post-solve-original-unit-feasibility-required",
        },
        "execution": {
            "worker_processes": WORKERS,
            "windows_python_processes": WINDOWS_PYTHON_PROCESSES,
            "wsl_python_processes": 0,
            "host_process_budget": HOST_PROCESS_BUDGET,
            "other_reserved_processes": 0,
            "native_threads_per_process": 1,
            "ready_job_cap": 16,
            "create_only": True,
            "retry_authorized": False,
            "terminal_only_observation": True,
        },
        "decision": {
            "unchanged_parent": "R345",
            "maximum_positive_classification": "RESIDUAL-PROBE-ELIGIBLE",
            "training_authorized": False,
        },
        "authorizations": {
            "simulation_authorized": False,
            "training_authorized": False,
            "distributed_runtime_authorized": False,
            "eval_authorized": False,
            "reward_design_authorized": False,
        },
    }


def _verify_frozen_inputs() -> None:
    r349._verify_frozen_inputs()
    for path, expected in EXPECTED_R349.items():
        actual = r347._sha256_file(path)
        if actual != expected:
            raise RuntimeError(f"frozen R349 input drift: {path}: {actual}")
        r347._verify_sidecar(path)
    sealed = r347._read_json(R349_SEAL)
    if sealed.get("round") != "R349" or not isinstance(sealed.get("sources"), dict):
        raise RuntimeError("R349 seal identity drift")
    for name, source in sealed["sources"].items():
        if name == "plan":
            continue
        path = ROOT / str(source["path"])
        if r347._sha256_file(path) != source["sha256"]:
            raise RuntimeError(f"R349 sealed source drift: {name}")
    current_plan = (ROOT / "memory/rounds/R349/plan.md").read_text(encoding="utf-8")
    if (
        "state: aborted" not in current_plan
        or "only six of sixteen oracle candidates" not in current_plan
    ):
        raise RuntimeError("R349 closed-plan boundary drift")
    diagnostic = r347._read_json(R349_DIAGNOSTIC)
    failure = r347._read_json(R349_FAILURE)
    if (
        len(diagnostic.get("rows", [])) != 16
        or diagnostic.get("scientific_result_authorized") is not False
        or failure.get("classification") != "ANALYSIS-INVALID"
        or failure.get("retry_authorized") is not False
    ):
        raise RuntimeError("R349 invalid-attempt boundary drift")


def _source_paths(include_rehearsal: bool) -> dict[str, Path]:
    paths = {
        "plan": PLAN,
        "adapter": Path(__file__).resolve(),
        "probe": ROOT / "probes/r350_smooth_convex_residual.py",
        "probe_tests": ROOT / "tests/test_r350_smooth_convex_residual.py",
        "adapter_tests": ROOT / "tests/test_r350_smooth_convex_residual_analysis.py",
        "solver": ROOT / "src/andes_rl_kundur/control/convex_residual_solver.py",
        "solver_tests": ROOT / "tests/test_convex_residual_solver.py",
        "certificate": ROOT / "src/andes_rl_kundur/control/convex_first_order_certificate.py",
        "parent_certificate": ROOT / "src/andes_rl_kundur/control/minimum_norm_certificate.py",
        "parent_certificate_tests": ROOT / "tests/test_minimum_norm_certificate.py",
        "r349_seal": R349_SEAL,
        "r349_attempt": R349_ATTEMPT,
        "r349_diagnostic": R349_DIAGNOSTIC,
        "r349_failure": R349_FAILURE,
        "r349_adapter": ROOT / "scripts/run_r349_certified_residual_analysis.py",
        "r349_probe": ROOT / "probes/r349_certified_residual.py",
        "r348_probe": ROOT / "probes/r348_fully_normalized_residual.py",
        "r345_adapter": ROOT / "scripts/run_r345_residual_headroom.py",
        "r345_probe": ROOT / "probes/r345_residual_headroom.py",
    }
    if include_rehearsal:
        paths["rehearsal"] = DEFAULT_REHEARSAL
    return paths


def _seal_sources() -> dict[str, dict[str, str]]:
    return {
        name: r347._source(path)
        for name, path in _source_paths(include_rehearsal=True).items()
    }


def _verify_entry_preconditions(out_dir: Path) -> list[dict[str, Any]]:
    _verify_frozen_inputs()
    plan_text = PLAN.read_text(encoding="utf-8")
    if "state: active" not in plan_text or "Q-0091" not in plan_text:
        raise RuntimeError("R350 active plan identity is missing")
    if out_dir.exists():
        raise FileExistsError(f"R350 result root already exists: {out_dir}")
    if WINDOWS_PYTHON_PROCESSES > HOST_PROCESS_BUDGET:
        raise RuntimeError("R350 process demand exceeds the host budget")
    if any(os.environ.get(name) != "1" for name in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    )):
        raise RuntimeError("R350 native numerical thread guard is not one")
    cases = r345._load_cases()
    if len(cases) != 16 or len({case["scenario_id"] for case in cases}) != 16:
        raise RuntimeError("R350 expected sixteen unique installed cases")
    return cases


def rehearsal(
    record_path: Path = DEFAULT_REHEARSAL,
    *,
    out_dir: Path = DEFAULT_OUT,
) -> str:
    """Run the formal entry's pre-attempt path without creating an attempt."""

    if DEFAULT_SEAL.exists():
        raise FileExistsError(f"R350 seal already exists: {DEFAULT_SEAL}")
    if record_path.exists():
        raise FileExistsError(f"R350 rehearsal already exists: {record_path}")
    cases = _verify_entry_preconditions(out_dir)
    return r347._write_new_json(
        record_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "contract_payload_sha256": r347._payload_sha256(build_contract()),
            "case_count": len(cases),
            "case_ids": [case["scenario_id"] for case in cases],
            "source_snapshot": {
                name: r347._source(path)
                for name, path in _source_paths(include_rehearsal=False).items()
            },
            "formal_output_absent": True,
            "attempt_created": False,
            "result_created": False,
            "native_threads_per_process": 1,
        },
    )


def prepare(seal_path: Path = DEFAULT_SEAL) -> str:
    """Create the source-bound R350 seal after a valid rehearsal."""

    if seal_path.exists():
        raise FileExistsError(f"R350 seal already exists: {seal_path}")
    _verify_entry_preconditions(DEFAULT_OUT)
    r347._verify_sidecar(DEFAULT_REHEARSAL)
    rehearsal_record = r347._read_json(DEFAULT_REHEARSAL)
    contract = build_contract()
    if (
        rehearsal_record.get("round") != ROUND_ID
        or rehearsal_record.get("contract_payload_sha256")
        != r347._payload_sha256(contract)
        or rehearsal_record.get("attempt_created") is not False
        or rehearsal_record.get("formal_output_absent") is not True
    ):
        raise RuntimeError("R350 rehearsal record drift")
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": r347._payload_sha256(contract),
        "sources": _seal_sources(),
        "result_root_absent_at_freeze": True,
        "retry_authorized": False,
    }
    return r347._write_new_json(seal_path, payload)


def load_seal(path: Path, expected_sha256: str) -> tuple[dict[str, Any], str]:
    """Verify the exact R350 seal and full source closure."""

    payload = r347._read_json(path)
    actual = r347._sha256_file(path)
    if actual != expected_sha256:
        raise RuntimeError(f"R350 seal digest mismatch: {actual}")
    contract = payload.get("contract")
    if (
        payload.get("round") != ROUND_ID
        or payload.get("question") != QUESTION_ID
        or contract != build_contract()
        or payload.get("contract_payload_sha256") != r347._payload_sha256(contract)
        or payload.get("sources") != _seal_sources()
    ):
        raise RuntimeError("R350 contract or source drift")
    _verify_entry_preconditions(DEFAULT_OUT)
    return payload, actual


def _certificate_payload(certificate: object) -> dict[str, Any]:
    return {
        "valid": bool(certificate.valid),
        "feasible": bool(certificate.feasible),
        "reason": str(certificate.reason),
        "active_constraint_count": int(certificate.active_constraint_count),
        "maximum_constraint_violation": float(certificate.maximum_constraint_violation),
        "stationarity_residual": float(certificate.stationarity_residual),
        "complementarity_residual": float(certificate.complementarity_residual),
        "optimality_tolerance": float(certificate.optimality_tolerance),
        "multipliers": certificate.multipliers.tolist(),
    }


def _start_payload(start: object) -> dict[str, Any]:
    result = start.result
    return {
        "name": str(start.name),
        "feasible": bool(result.feasible),
        "optimizer_status_success": bool(result.optimizer_status_success),
        "target_feasible": bool(result.target_feasible),
        "message": str(result.message),
        "solver_iterations": int(result.solver_iterations),
        "maximum_constraint_residual": float(result.maximum_constraint_residual),
        "maximum_target_shortfall": float(result.maximum_target_shortfall),
        "objective_value": float(result.objective_value),
        "certificate": _certificate_payload(result.certificate),
    }


def _oracle_worker(case: dict[str, Any]) -> dict[str, Any]:
    from probes.r345_residual_headroom import build_control_response_map, endpoint_values
    from probes.r350_smooth_convex_residual import solve_three_start_edge_residual

    from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits

    started = time.perf_counter()
    limits = FeedbackLimits()
    response = build_control_response_map(
        case["model"], horizon=case["base_outputs"].shape[0]
    )
    solved = solve_three_start_edge_residual(
        base_outputs=case["base_outputs"],
        base_node_commands=case["base_node_commands"],
        previous_node_command=case["previous_node_command"],
        initial_soc=case["initial_soc"],
        response_map=response,
        limits=limits,
        minimum_improvement_fraction=r345.MINIMUM_IMPROVEMENT,
        maximum_iterations=r345.MAXIMUM_ITERATIONS,
        function_tolerance=r345.FUNCTION_TOLERANCE,
        feasibility_tolerance=r345.FEASIBILITY_TOLERANCE,
    )
    starts = [_start_payload(start) for start in solved.starts]
    selected = solved.selected
    base = endpoint_values(
        case["base_outputs"], sample_period_seconds=limits.sample_period_seconds
    )
    zero = endpoint_values(
        case["zero_outputs"], sample_period_seconds=limits.sample_period_seconds
    )
    if selected is None:
        return {
            "scenario_id": case["scenario_id"],
            "worker_pid": os.getpid(),
            "elapsed_seconds": time.perf_counter() - started,
            "feasible": False,
            "optimizer_valid": False,
            "target_feasible": False,
            "message": "no fixed R350 start passed the independent certificate",
            "solver_iterations": int(sum(item["solver_iterations"] for item in starts)),
            "maximum_constraint_residual": float(
                max(item["maximum_constraint_residual"] for item in starts)
            ),
            "maximum_target_shortfall": float(
                max(item["maximum_target_shortfall"] for item in starts)
            ),
            "objective_value": float("inf"),
            "base_endpoints": base,
            "zero_control_endpoints": zero,
            "selected_start": None,
            "certified_start_count": 0,
            "r348_optimizer_valid": solved.r348_optimizer_valid,
            "starts": starts,
        }
    _counterfactual, nominal, robust = r345._candidate_endpoints(
        case, selected.edge_actions
    )
    return {
        "scenario_id": case["scenario_id"],
        "worker_pid": os.getpid(),
        "elapsed_seconds": time.perf_counter() - started,
        "feasible": True,
        "optimizer_valid": True,
        "target_feasible": bool(selected.target_feasible),
        "message": selected.message,
        "solver_iterations": selected.solver_iterations,
        "maximum_constraint_residual": selected.maximum_constraint_residual,
        "maximum_target_shortfall": selected.maximum_target_shortfall,
        "objective_value": selected.objective_value,
        "base_endpoints": base,
        "zero_control_endpoints": zero,
        "nominal_endpoints": nominal,
        "mismatch_bounded_endpoints": robust,
        "edge_actions": selected.edge_actions.tolist(),
        "residual_node_actions": selected.residual_node_actions.tolist(),
        "counterfactual_node_commands": selected.counterfactual_node_commands.tolist(),
        "counterfactual_soc": selected.counterfactual_soc.tolist(),
        "selected_start": solved.selected_start,
        "certified_start_count": solved.certified_start_count,
        "r348_optimizer_valid": solved.r348_optimizer_valid,
        "certificate": _certificate_payload(selected.certificate),
        "starts": starts,
    }


def _project_oracle_diagnostic(
    case: dict[str, Any], worker: dict[str, Any]
) -> dict[str, Any]:
    projected = r347.project_oracle_diagnostic(case, worker)
    projected.update(
        {
            "selected_start": worker.get("selected_start"),
            "certified_start_count": int(worker["certified_start_count"]),
            "r348_optimizer_valid": bool(worker["r348_optimizer_valid"]),
            "starts": worker["starts"],
        }
    )
    if "certificate" in worker:
        projected["certificate"] = worker["certificate"]
    return projected


def analyse(expected_sha256: str, *, out_dir: Path = DEFAULT_OUT) -> str:
    """Execute the one sealed, create-only R350 analysis attempt."""

    seal, seal_digest = load_seal(DEFAULT_SEAL, expected_sha256)
    out_dir.mkdir(parents=True, exist_ok=False)
    attempt_path = out_dir / "analysis_attempt.json"
    attempt_digest = r347._write_new_json(
        attempt_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "worker_processes": WORKERS,
            "windows_python_processes": WINDOWS_PYTHON_PROCESSES,
            "native_threads_per_process": 1,
            "retry_authorized": False,
            "andes_executed": False,
            "training_executed": False,
            "distributed_runtime_executed": False,
            "eval_executed": False,
        },
    )
    started = time.perf_counter()
    try:
        cases = r345._load_cases()
        if len(cases) != 16 or len({case["scenario_id"] for case in cases}) != 16:
            raise RuntimeError("R350 expected sixteen unique R345 cases")
        with ProcessPoolExecutor(max_workers=WORKERS) as executor:
            oracle = list(executor.map(_oracle_worker, cases))
            diagnostic_path = out_dir / "oracle_diagnostic.json"
            diagnostic_digest = r347._write_new_json(
                diagnostic_path,
                {
                    "schema_version": 1,
                    "round": ROUND_ID,
                    "created_utc": datetime.now(UTC).isoformat(),
                    "rows": [
                        _project_oracle_diagnostic(case, worker)
                        for case, worker in zip(cases, oracle, strict=True)
                    ],
                    "scientific_result_authorized": False,
                    "training_authorized": False,
                },
            )
            if not all(row["optimizer_valid"] for row in oracle):
                raise RuntimeError(
                    "one or more R350 oracle cases lacked a certified fixed start"
                )
            proposals = r345._local_proposals(cases, oracle)
            local = list(
                executor.map(r345._local_worker, zip(cases, proposals, strict=True))
            )
        if not all(row["feasible"] for row in local):
            raise RuntimeError("one or more R350 local projections were invalid")
        decision = r345._classify(cases, oracle, local)
        case_identity = [
            {
                "scenario_id": case["scenario_id"],
                "point": case["point"],
                "channel": case["channel"],
                "sign": case["sign"],
                "mismatch_envelope": case["mismatch_envelope"].tolist(),
                "parent_record_index": case["parent_record_index"],
                "parent_trace": case["parent_trace"],
                "zero_parent_record_index": case["zero_parent_record_index"],
                "zero_parent_trace": case["zero_parent_trace"],
            }
            for case in cases
        ]
        analysis_path = out_dir / "analysis.json"
        analysis_digest = r347._write_new_json(
            analysis_path,
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "created_utc": datetime.now(UTC).isoformat(),
                "seal_sha256": seal_digest,
                "contract_payload_sha256": seal["contract_payload_sha256"],
                "analysis_attempt_sha256": attempt_digest,
                "oracle_diagnostic_sha256": diagnostic_digest,
                "elapsed_seconds": time.perf_counter() - started,
                "worker_processes": WORKERS,
                "oracle_unique_worker_pids": len({row["worker_pid"] for row in oracle}),
                "local_unique_worker_pids": len({row["worker_pid"] for row in local}),
                "case_identity": case_identity,
                "oracle": oracle,
                "neighbour_local": local,
                **decision,
                "andes_executed": False,
                "physical_trajectory_created": False,
                "training_executed": False,
                "reward_defined": False,
                "architecture_selected": False,
                "distributed_runtime_executed": False,
                "eval_executed": False,
            },
        )
        manifest_digest = r347._write_new_json(
            out_dir / "manifest.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "entries": [
                    {
                        "path": attempt_path.relative_to(ROOT).as_posix(),
                        "sha256": attempt_digest,
                    },
                    {
                        "path": diagnostic_path.relative_to(ROOT).as_posix(),
                        "sha256": diagnostic_digest,
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
        failure_path = out_dir / "failure.json"
        if not failure_path.exists():
            r347._write_new_json(
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
                    "training_authorized": False,
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
    analyse_parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
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
        analyse(args.expected_seal_sha256, out_dir=args.out)
        return 0
    raise AssertionError(f"unexpected command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
