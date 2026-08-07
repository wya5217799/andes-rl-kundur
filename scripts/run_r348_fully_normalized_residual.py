"""Seal and execute the fully normalized R348 residual-headroom analysis."""

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

ROUND_ID = "R348"
QUESTION_ID = "Q-0091"
WORKERS = 16
DEFAULT_SEAL = ROOT / "memory/rounds/R348/analysis_seal.json"
DEFAULT_OUT = ROOT / "results/r348_fully_normalized_residual"
PLAN = ROOT / "memory/rounds/R348/plan.md"
R347_SEAL = ROOT / "memory/rounds/R347/analysis_seal.json"
R347_ATTEMPT = ROOT / "results/r347_scale_stable_residual/analysis_attempt.json"
R347_DIAGNOSTIC = ROOT / "results/r347_scale_stable_residual/oracle_diagnostic.json"
R347_FAILURE = ROOT / "results/r347_scale_stable_residual/failure.json"
EXPECTED_R347_INPUTS = {
    "memory/rounds/R347/analysis_seal.json": (
        "f91a223aac0d96435230ebc371ae398a7e300e9e9327fbf1320fbe02790e22e7"
    ),
    "results/r347_scale_stable_residual/analysis_attempt.json": (
        "d36dba38e4c974f1b02b9e82b5488d3fc14993ac69d34910bc8dd25ae9098db3"
    ),
    "results/r347_scale_stable_residual/oracle_diagnostic.json": (
        "608169c63d5bd5eb16c7b01fa753d5dc49d2b6b705b1f333ed72608d0c914399"
    ),
    "results/r347_scale_stable_residual/failure.json": (
        "feb8ea6f9b4d2dacbd0584b8afb0342a0857f4a45897a98530a1db45747b6a69"
    ),
    "scripts/run_r347_scale_stable_residual.py": (
        "1cd2c145f072d1baacea3a968c6624ae69cab9701739bf3b3020df3ab410fcb1"
    ),
    "probes/r347_scale_stable_residual.py": (
        "961557471133fabe8f2b01b7afd0e2eab3349b94cbc373abafda30f42219fff8"
    ),
    "tests/test_r347_scale_stable_residual.py": (
        "cb8bd5172fdefea78a8e45d006d890efeb090ed4a891604938162c3adeb5a2d4"
    ),
}


def build_contract() -> dict[str, Any]:
    """Return R345 science with only fixed positive numerical scalings."""

    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "create-only-fully-normalized-residual-headroom",
        "parent_scientific_contract_payload_sha256": r347.PARENT_CONTRACT_SHA256,
        "parent_scientific_contract": r345.build_contract(),
        "numerical_repair": {
            "relative_endpoint_slacks": True,
            "edge_variable_scale": "frozen-node-ramp",
            "endpoint_constraint_scale": "scenario-baseline-endpoint",
            "power_constraint_scale": "frozen-node-power",
            "ramp_constraint_scale": "frozen-node-ramp",
            "soc_constraint_scale": "frozen-soc-span",
            "scientific_feasible_set_changed": False,
            "minimum_norm_solution_changed": False,
        },
        "execution": {
            "worker_processes": WORKERS,
            "native_threads_per_process": 1,
            "ready_job_cap": 16,
            "other_reserved_processes": 0,
            "create_only": True,
            "retry_authorized": False,
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
    r347._verify_frozen_inputs()
    for relative, expected in EXPECTED_R347_INPUTS.items():
        actual = r347._sha256_file(ROOT / relative)
        if actual != expected:
            raise RuntimeError(f"frozen R347 input drift: {relative}: {actual}")
    for path in (R347_SEAL, R347_ATTEMPT, R347_DIAGNOSTIC, R347_FAILURE):
        r347._verify_sidecar(path)

    seal = r347._read_json(R347_SEAL)
    sources = seal.get("sources")
    if not isinstance(sources, dict):
        raise RuntimeError("R347 source inventory is missing")
    for key in ("adapter", "probe", "tests"):
        source = sources.get(key)
        if not isinstance(source, dict):
            raise RuntimeError(f"R347 source is missing: {key}")
        if r347._sha256_file(ROOT / str(source.get("path"))) != source.get("sha256"):
            raise RuntimeError(f"R347 sealed source drift: {key}")

    diagnostic = r347._read_json(R347_DIAGNOSTIC)
    failure = r347._read_json(R347_FAILURE)
    invalid_rows = [
        row for row in diagnostic.get("rows", []) if row.get("optimizer_valid") is False
    ]
    if (
        len(invalid_rows) != 1
        or invalid_rows[0].get("target_feasible") is not True
        or "minimum norm" not in str(invalid_rows[0].get("message", ""))
        or failure.get("classification") != "ANALYSIS-INVALID"
        or failure.get("retry_authorized") is not False
    ):
        raise RuntimeError("R347 minimum-norm diagnosis drift")


def _seal_sources() -> dict[str, dict[str, str]]:
    paths = {
        "plan": PLAN,
        "adapter": Path(__file__).resolve(),
        "probe": ROOT / "probes/r348_fully_normalized_residual.py",
        "tests": ROOT / "tests/test_r348_fully_normalized_residual.py",
        "r347_seal": R347_SEAL,
        "r347_attempt": R347_ATTEMPT,
        "r347_diagnostic": R347_DIAGNOSTIC,
        "r347_failure": R347_FAILURE,
        "r347_adapter": ROOT / "scripts/run_r347_scale_stable_residual.py",
        "r347_probe": ROOT / "probes/r347_scale_stable_residual.py",
        "r347_tests": ROOT / "tests/test_r347_scale_stable_residual.py",
        "r345_adapter": ROOT / "scripts/run_r345_residual_headroom.py",
        "r345_probe": ROOT / "probes/r345_residual_headroom.py",
    }
    return {name: r347._source(path) for name, path in paths.items()}


def prepare(seal_path: Path = DEFAULT_SEAL) -> str:
    """Create the source-bound R348 seal."""

    _verify_frozen_inputs()
    if seal_path.exists():
        raise FileExistsError(f"R348 seal already exists: {seal_path}")
    if DEFAULT_OUT.exists():
        raise FileExistsError(f"R348 result root already exists: {DEFAULT_OUT}")
    plan_text = PLAN.read_text(encoding="utf-8")
    if "state: active" not in plan_text or "Q-0091" not in plan_text:
        raise RuntimeError("R348 active plan identity is missing")
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
    """Verify the exact R348 seal and source closure."""

    payload = r347._read_json(path)
    actual = r347._sha256_file(path)
    if actual != expected_sha256:
        raise RuntimeError(f"R348 seal digest mismatch: {actual}")
    contract = payload.get("contract")
    if (
        payload.get("round") != ROUND_ID
        or payload.get("question") != QUESTION_ID
        or contract != build_contract()
        or payload.get("contract_payload_sha256") != r347._payload_sha256(contract)
    ):
        raise RuntimeError("R348 contract drift")
    if payload.get("sources") != _seal_sources():
        raise RuntimeError("R348 source drift")
    _verify_frozen_inputs()
    return payload, actual


def _oracle_worker(case: dict[str, Any]) -> dict[str, Any]:
    from probes.r345_residual_headroom import (
        build_control_response_map,
        endpoint_values,
    )
    from probes.r348_fully_normalized_residual import (
        solve_fully_normalized_minimum_norm_edge_residual,
    )

    from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits

    started = time.perf_counter()
    limits = FeedbackLimits()
    response = build_control_response_map(
        case["model"],
        horizon=case["base_outputs"].shape[0],
    )
    solution = solve_fully_normalized_minimum_norm_edge_residual(
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
        "target_feasible": bool(solution.target_feasible),
        "message": solution.message,
        "solver_iterations": solution.solver_iterations,
        "maximum_constraint_residual": solution.maximum_constraint_residual,
        "maximum_target_shortfall": solution.maximum_target_shortfall,
        "objective_value": solution.objective_value,
        "base_endpoints": base,
        "zero_control_endpoints": zero,
        "nominal_endpoints": nominal,
        "mismatch_bounded_endpoints": robust,
        "edge_actions": solution.edge_actions.tolist(),
        "residual_node_actions": solution.residual_node_actions.tolist(),
        "counterfactual_node_commands": solution.counterfactual_node_commands.tolist(),
        "counterfactual_soc": solution.counterfactual_soc.tolist(),
    }


def analyse(expected_sha256: str, *, out_dir: Path = DEFAULT_OUT) -> str:
    """Execute the one sealed, create-only R348 analysis attempt."""

    seal, seal_digest = load_seal(DEFAULT_SEAL, expected_sha256)
    if out_dir.exists():
        raise FileExistsError(f"R348 result root already exists: {out_dir}")
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
            raise RuntimeError("R348 expected sixteen unique R345 cases")
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
                        r347.project_oracle_diagnostic(case, worker)
                        for case, worker in zip(cases, oracle, strict=True)
                    ],
                    "scientific_result_authorized": False,
                    "training_authorized": False,
                },
            )
            if not all(row["optimizer_valid"] for row in oracle):
                raise RuntimeError("one or more R348 oracle optimizers were not valid")
            proposals = r345._local_proposals(cases, oracle)
            local = list(executor.map(r345._local_worker, zip(cases, proposals, strict=True)))
        if not all(row["feasible"] for row in local):
            raise RuntimeError("one or more R348 local projections were not valid")
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
