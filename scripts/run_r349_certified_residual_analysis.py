"""Seal and execute the independently certified R349 residual analysis."""

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
from scripts import run_r348_fully_normalized_residual as r348  # noqa: E402

ROUND_ID = "R349"
QUESTION_ID = "Q-0091"
WORKERS = 16
DEFAULT_SEAL = ROOT / "memory/rounds/R349/analysis_seal.json"
DEFAULT_OUT = ROOT / "results/r349_certified_residual_analysis"
PLAN = ROOT / "memory/rounds/R349/plan.md"
R348_SEAL = ROOT / "memory/rounds/R348/analysis_seal.json"
R348_ATTEMPT = ROOT / "results/r348_fully_normalized_residual/analysis_attempt.json"
R348_DIAGNOSTIC = ROOT / "results/r348_fully_normalized_residual/oracle_diagnostic.json"
R348_FAILURE = ROOT / "results/r348_fully_normalized_residual/failure.json"
EXPECTED_R348_INPUTS = {
    "memory/rounds/R348/analysis_seal.json": (
        "b95b75b97c82b2f04a0d356fc2b6771456e86f029deaf405e33ec8575fe24601"
    ),
    "results/r348_fully_normalized_residual/analysis_attempt.json": (
        "9bc9718800fdc9c83ba60014536d4b50e3ce5ea82d75d8452f091ee6a9bb27bc"
    ),
    "results/r348_fully_normalized_residual/oracle_diagnostic.json": (
        "6ffa94ed85d878805018f7ea9a947102ed96df2de46d276a627c4680a0167dc7"
    ),
    "results/r348_fully_normalized_residual/failure.json": (
        "1bba71c77f6cc64da06077f572bd125a4322e37d61ac7d18a4ebb97791dec00f"
    ),
    "scripts/run_r348_fully_normalized_residual.py": (
        "a0672fd0d643e6c69ea67d702d70dffa12336ac10bc28a633fb001d59cf7bffb"
    ),
    "probes/r348_fully_normalized_residual.py": (
        "e766a1e8573051eb185adab00e6e4a08d6130f07f075507da20bf53b8b26b976"
    ),
    "tests/test_r348_fully_normalized_residual.py": (
        "4c420a67b47de00ebbe98cf70272d36da15264ac76a46beae2cbd0801551194b"
    ),
}


def build_contract() -> dict[str, Any]:
    """Return the unchanged R348 contract plus one acceptance certificate."""

    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "create-only-independently-certified-residual-headroom",
        "parent_scientific_contract_payload_sha256": r347.PARENT_CONTRACT_SHA256,
        "parent_numerical_contract": r348.build_contract(),
        "acceptance_certificate": {
            "objective": "minimum-dimensionless-edge-two-norm-squared",
            "constraint_convention": ("dimensionless-g-greater-than-or-equal-to-zero"),
            "feasibility_tolerance_original_units": 1.0e-8,
            "active_and_optimality_tolerance": 1.0e-4,
            "jacobian": "central-cbrt-machine-epsilon-relative-step",
            "multipliers": "nonnegative-least-squares",
            "requires_stationarity": True,
            "requires_complementarity": True,
            "upper_soc_guard": ("dimensionless-slack-strictly-greater-than-1e-4"),
            "candidate_changed": False,
            "scientific_contract_changed": False,
        },
        "execution": {
            "worker_processes": WORKERS,
            "native_threads_per_process": 1,
            "ready_job_cap": 16,
            "other_reserved_processes": 0,
            "create_only": True,
            "retry_authorized": False,
            "terminal_only_observation": True,
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
    r348._verify_frozen_inputs()
    for relative, expected in EXPECTED_R348_INPUTS.items():
        actual = r347._sha256_file(ROOT / relative)
        if actual != expected:
            raise RuntimeError(f"frozen R348 input drift: {relative}: {actual}")
    for path in (R348_SEAL, R348_ATTEMPT, R348_DIAGNOSTIC, R348_FAILURE):
        r347._verify_sidecar(path)

    seal = r347._read_json(R348_SEAL)
    sources = seal.get("sources")
    if not isinstance(sources, dict):
        raise RuntimeError("R348 source inventory is missing")
    for key in ("adapter", "probe", "tests"):
        source = sources.get(key)
        if not isinstance(source, dict):
            raise RuntimeError(f"R348 source is missing: {key}")
        if r347._sha256_file(ROOT / str(source.get("path"))) != source.get("sha256"):
            raise RuntimeError(f"R348 sealed source drift: {key}")

    diagnostic = r347._read_json(R348_DIAGNOSTIC)
    failure = r347._read_json(R348_FAILURE)
    invalid_rows = [
        row for row in diagnostic.get("rows", []) if row.get("optimizer_valid") is False
    ]
    if (
        len(invalid_rows) != 6
        or not all(row.get("target_feasible") is True for row in invalid_rows)
        or not all(
            float(row.get("maximum_constraint_residual", float("inf")))
            <= r345.FEASIBILITY_TOLERANCE
            for row in invalid_rows
        )
        or failure.get("classification") != "ANALYSIS-INVALID"
        or failure.get("retry_authorized") is not False
    ):
        raise RuntimeError("R348 feasible-candidate diagnosis drift")


def _seal_sources() -> dict[str, dict[str, str]]:
    paths = {
        "plan": PLAN,
        "adapter": Path(__file__).resolve(),
        "probe": ROOT / "probes/r349_certified_residual.py",
        "tests": ROOT / "tests/test_r349_certified_residual.py",
        "adapter_tests": ROOT / "tests/test_r349_certified_residual_analysis.py",
        "certificate": (ROOT / "src/andes_rl_kundur/control/minimum_norm_certificate.py"),
        "certificate_tests": ROOT / "tests/test_minimum_norm_certificate.py",
        "r348_seal": R348_SEAL,
        "r348_attempt": R348_ATTEMPT,
        "r348_diagnostic": R348_DIAGNOSTIC,
        "r348_failure": R348_FAILURE,
        "r348_adapter": ROOT / "scripts/run_r348_fully_normalized_residual.py",
        "r348_probe": ROOT / "probes/r348_fully_normalized_residual.py",
        "r348_tests": ROOT / "tests/test_r348_fully_normalized_residual.py",
        "r345_adapter": ROOT / "scripts/run_r345_residual_headroom.py",
        "r345_probe": ROOT / "probes/r345_residual_headroom.py",
    }
    return {name: r347._source(path) for name, path in paths.items()}


def prepare(seal_path: Path = DEFAULT_SEAL) -> str:
    """Create the source-bound R349 seal."""

    _verify_frozen_inputs()
    if seal_path.exists():
        raise FileExistsError(f"R349 seal already exists: {seal_path}")
    if DEFAULT_OUT.exists():
        raise FileExistsError(f"R349 result root already exists: {DEFAULT_OUT}")
    plan_text = PLAN.read_text(encoding="utf-8")
    if "state: active" not in plan_text or "Q-0091" not in plan_text:
        raise RuntimeError("R349 active plan identity is missing")
    contract = build_contract()
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
    """Verify the exact R349 seal and source closure."""

    payload = r347._read_json(path)
    actual = r347._sha256_file(path)
    if actual != expected_sha256:
        raise RuntimeError(f"R349 seal digest mismatch: {actual}")
    contract = payload.get("contract")
    if (
        payload.get("round") != ROUND_ID
        or payload.get("question") != QUESTION_ID
        or contract != build_contract()
        or payload.get("contract_payload_sha256") != r347._payload_sha256(contract)
    ):
        raise RuntimeError("R349 contract drift")
    if payload.get("sources") != _seal_sources():
        raise RuntimeError("R349 source drift")
    _verify_frozen_inputs()
    return payload, actual


def _certificate_payload(certificate: object | None) -> dict[str, Any] | None:
    if certificate is None:
        return None
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


def _oracle_worker(case: dict[str, Any]) -> dict[str, Any]:
    from probes.r345_residual_headroom import (
        build_control_response_map,
        endpoint_values,
    )
    from probes.r349_certified_residual import (
        solve_certified_fully_normalized_minimum_norm_edge_residual,
    )

    from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits

    started = time.perf_counter()
    limits = FeedbackLimits()
    response = build_control_response_map(
        case["model"],
        horizon=case["base_outputs"].shape[0],
    )
    certified = solve_certified_fully_normalized_minimum_norm_edge_residual(
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
    solution = certified.solution
    base = endpoint_values(
        case["base_outputs"],
        sample_period_seconds=limits.sample_period_seconds,
    )
    zero = endpoint_values(
        case["zero_outputs"],
        sample_period_seconds=limits.sample_period_seconds,
    )
    _counterfactual, nominal, robust = r345._candidate_endpoints(
        case,
        solution.edge_actions,
    )
    return {
        "scenario_id": case["scenario_id"],
        "worker_pid": os.getpid(),
        "elapsed_seconds": time.perf_counter() - started,
        "feasible": bool(solution.feasible),
        "optimizer_valid": bool(solution.optimizer_valid),
        "base_optimizer_valid": bool(certified.base_optimizer_valid),
        "target_feasible": bool(solution.target_feasible),
        "message": solution.message,
        "solver_iterations": solution.solver_iterations,
        "maximum_constraint_residual": solution.maximum_constraint_residual,
        "maximum_target_shortfall": solution.maximum_target_shortfall,
        "objective_value": solution.objective_value,
        "certificate": _certificate_payload(certified.certificate),
        "base_endpoints": base,
        "zero_control_endpoints": zero,
        "nominal_endpoints": nominal,
        "mismatch_bounded_endpoints": robust,
        "edge_actions": solution.edge_actions.tolist(),
        "residual_node_actions": solution.residual_node_actions.tolist(),
        "counterfactual_node_commands": (solution.counterfactual_node_commands.tolist()),
        "counterfactual_soc": solution.counterfactual_soc.tolist(),
    }


def _project_oracle_diagnostic(
    case: dict[str, Any],
    worker: dict[str, Any],
) -> dict[str, Any]:
    projected = r347.project_oracle_diagnostic(case, worker)
    projected["base_optimizer_valid"] = bool(worker["base_optimizer_valid"])
    projected["certificate"] = worker["certificate"]
    return projected


def analyse(expected_sha256: str, *, out_dir: Path = DEFAULT_OUT) -> str:
    """Execute the one sealed, create-only R349 analysis attempt."""

    seal, seal_digest = load_seal(DEFAULT_SEAL, expected_sha256)
    if out_dir.exists():
        raise FileExistsError(f"R349 result root already exists: {out_dir}")
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
            raise RuntimeError("R349 expected sixteen unique R345 cases")
        with ProcessPoolExecutor(max_workers=WORKERS) as executor:
            oracle = list(executor.map(_oracle_worker, cases))
            oracle_diagnostic_path = out_dir / "oracle_diagnostic.json"
            oracle_diagnostic_digest = r347._write_new_json(
                oracle_diagnostic_path,
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
                raise RuntimeError("one or more R349 oracle candidates lacked a valid certificate")
            proposals = r345._local_proposals(cases, oracle)
            local = list(executor.map(r345._local_worker, zip(cases, proposals, strict=True)))
        if not all(row["feasible"] for row in local):
            raise RuntimeError("one or more R349 local projections were not valid")
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
                "oracle_diagnostic_sha256": oracle_diagnostic_digest,
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
                        "path": oracle_diagnostic_path.relative_to(ROOT).as_posix(),
                        "sha256": oracle_diagnostic_digest,
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
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    analyse_parser = subparsers.add_parser("analyse")
    analyse_parser.add_argument("--expected-sha256", required=True)
    analyse_parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "prepare":
        print(prepare(args.seal), flush=True)
        return 0
    if args.command == "analyse":
        analyse(args.expected_sha256, out_dir=args.out)
        return 0
    raise AssertionError(f"unexpected command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
