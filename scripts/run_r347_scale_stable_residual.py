"""Seal and execute the scale-stable R347 residual-headroom analysis."""

from __future__ import annotations

import argparse
import hashlib
import json
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

ROUND_ID = "R347"
QUESTION_ID = "Q-0091"
WORKERS = 16
DEFAULT_SEAL = ROOT / "memory/rounds/R347/analysis_seal.json"
DEFAULT_OUT = ROOT / "results/r347_scale_stable_residual"
PLAN = ROOT / "memory/rounds/R347/plan.md"
R345_SEAL = ROOT / "memory/rounds/R345/analysis_seal.json"
R345_FAILURE = ROOT / "results/r345_residual_headroom/failure.json"
R346_SEAL = ROOT / "memory/rounds/R346/diagnostic_seal.json"
R346_DIAGNOSTIC = ROOT / "results/r346_r345_optimizer_diagnosis/diagnostic.json"
R346_MANIFEST = ROOT / "results/r346_r345_optimizer_diagnosis/manifest.json"
EXPECTED_FROZEN_INPUTS = {
    "memory/rounds/R345/analysis_seal.json": (
        "47f1b287316f1475725a2c844f470016058ec06f5759d1d743829c74afbc04f4"
    ),
    "results/r345_residual_headroom/failure.json": (
        "8a519fb736151ea793f18cff2b0d08de65d810dd8f49425104cd9f68de08c9a3"
    ),
    "memory/rounds/R346/diagnostic_seal.json": (
        "d5863b23b8c827fdd56782e09ca76a69af7046c1b5b2e4a7b123a4dc1fc5cb5a"
    ),
    "results/r346_r345_optimizer_diagnosis/diagnostic.json": (
        "8d3e9482b55167622b81f0e574b29a968d427fa944afe65ddc7383f51c1b3d41"
    ),
    "results/r346_r345_optimizer_diagnosis/manifest.json": (
        "1964cfcfed8a78a413067e726102ae4ac2b20cbc78375230e327e8315965ad70"
    ),
    "scripts/run_r345_residual_headroom.py": (
        "97f598cfe63694c5028ee37a2acbb9b31ed94d8d6d1a36635082ff3745c935fb"
    ),
    "probes/r345_residual_headroom.py": (
        "e175020e592064361c40b63ad6cb5f44db430529abd033a6a47a128aebaa344a"
    ),
    "tests/test_r345_residual_headroom.py": (
        "8f8deccfb79af7a93039cc42402451c2d610cf7215d6b63ae416ceb7a0af5e84"
    ),
}
PARENT_CONTRACT_SHA256 = "6492c9a8b087eabcd41222b3bb246c167936e1e82f8de33b5de3a6daf41fd1ab"
REUSED_R345_SOURCE_KEYS = (
    "adapter",
    "probe",
    "tests",
    "r344_adapter",
    "separate_input",
    "physical_bridge_metrics",
    "offline_limits",
    "formal_seal",
    "formal_execution",
    "formal_analysis",
    "formal_manifest",
    "candidate_models",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _payload_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


def _write_new_json(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(serialized)
    except FileExistsError:
        raise FileExistsError(f"create-only output already exists: {path}") from None
    digest = _sha256_file(path)
    sidecar = Path(f"{path}.sha256")
    try:
        with sidecar.open("x", encoding="ascii", newline="\n") as handle:
            handle.write(f"{digest}  {path.name}\n")
    except FileExistsError:
        raise FileExistsError(f"create-only sidecar already exists: {sidecar}") from None
    return digest


def _source(path: Path) -> dict[str, str]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": _sha256_file(path),
    }


def _verify_sidecar(path: Path) -> None:
    recorded = Path(f"{path}.sha256").read_text(encoding="ascii").split()[0]
    if recorded != _sha256_file(path):
        raise RuntimeError(f"sidecar mismatch: {path}")


def build_contract() -> dict[str, Any]:
    """Return R345 science with only the R347 slack reparameterization."""

    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "stage": "create-only-scale-stable-residual-headroom",
        "parent_scientific_contract_payload_sha256": PARENT_CONTRACT_SHA256,
        "parent_scientific_contract": r345.build_contract(),
        "numerical_repair": {
            "absolute_slack_replaced": True,
            "relative_slack_initial": [0.02, 0.02],
            "relative_slack_objective": "sum-of-squared-relative-shortfalls",
            "scientific_feasible_set_changed": False,
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
    for relative, expected in EXPECTED_FROZEN_INPUTS.items():
        actual = _sha256_file(ROOT / relative)
        if actual != expected:
            raise RuntimeError(f"frozen parent drift: {relative}: {actual}")
    for path in (
        R345_SEAL,
        R345_FAILURE,
        R346_SEAL,
        R346_DIAGNOSTIC,
        R346_MANIFEST,
    ):
        _verify_sidecar(path)

    parent_seal = _read_json(R345_SEAL)
    if parent_seal.get("contract_payload_sha256") != PARENT_CONTRACT_SHA256:
        raise RuntimeError("R345 scientific contract identity drift")
    if parent_seal.get("contract") != r345.build_contract():
        raise RuntimeError("R345 scientific contract content drift")
    sources = parent_seal.get("sources")
    if not isinstance(sources, dict):
        raise RuntimeError("R345 source inventory is missing")
    for key in REUSED_R345_SOURCE_KEYS:
        source = sources.get(key)
        if not isinstance(source, dict):
            raise RuntimeError(f"R345 source is missing: {key}")
        if _sha256_file(ROOT / str(source.get("path"))) != source.get("sha256"):
            raise RuntimeError(f"R345 reused source drift: {key}")

    failure = _read_json(R345_FAILURE)
    diagnostic = _read_json(R346_DIAGNOSTIC)
    if (
        failure.get("classification") != "ANALYSIS-INVALID"
        or failure.get("retry_authorized") is not False
        or diagnostic.get("classification") != "RELAXATION-INVALID"
        or diagnostic.get("scientific_result_authorized") is not False
        or diagnostic.get("training_authorized") is not False
    ):
        raise RuntimeError("R345/R346 failure diagnosis drift")


def _seal_sources() -> dict[str, dict[str, str]]:
    paths = {
        "plan": PLAN,
        "adapter": Path(__file__).resolve(),
        "probe": ROOT / "probes/r347_scale_stable_residual.py",
        "tests": ROOT / "tests/test_r347_scale_stable_residual.py",
        "r345_seal": R345_SEAL,
        "r345_failure": R345_FAILURE,
        "r346_seal": R346_SEAL,
        "r346_diagnostic": R346_DIAGNOSTIC,
        "r346_manifest": R346_MANIFEST,
        "r345_adapter": ROOT / "scripts/run_r345_residual_headroom.py",
        "r345_probe": ROOT / "probes/r345_residual_headroom.py",
        "r345_tests": ROOT / "tests/test_r345_residual_headroom.py",
    }
    return {name: _source(path) for name, path in paths.items()}


def prepare(seal_path: Path = DEFAULT_SEAL) -> str:
    """Create the source-bound R347 seal."""

    _verify_frozen_inputs()
    if seal_path.exists():
        raise FileExistsError(f"R347 seal already exists: {seal_path}")
    if DEFAULT_OUT.exists():
        raise FileExistsError(f"R347 result root already exists: {DEFAULT_OUT}")
    plan_text = PLAN.read_text(encoding="utf-8")
    if "state: active" not in plan_text or "Q-0091" not in plan_text:
        raise RuntimeError("R347 active plan identity is missing")
    contract = build_contract()
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_payload_sha256": _payload_sha256(contract),
        "sources": _seal_sources(),
        "result_root_absent_at_freeze": True,
        "retry_authorized": False,
    }
    return _write_new_json(seal_path, payload)


def load_seal(path: Path, expected_sha256: str) -> tuple[dict[str, Any], str]:
    """Verify the exact R347 seal and source closure."""

    payload = _read_json(path)
    actual = _sha256_file(path)
    if actual != expected_sha256:
        raise RuntimeError(f"R347 seal digest mismatch: {actual}")
    contract = payload.get("contract")
    if (
        payload.get("round") != ROUND_ID
        or payload.get("question") != QUESTION_ID
        or contract != build_contract()
        or payload.get("contract_payload_sha256") != _payload_sha256(contract)
    ):
        raise RuntimeError("R347 contract drift")
    if payload.get("sources") != _seal_sources():
        raise RuntimeError("R347 source drift")
    _verify_frozen_inputs()
    return payload, actual


def _oracle_worker(case: dict[str, Any]) -> dict[str, Any]:
    from probes.r345_residual_headroom import (
        build_control_response_map,
        endpoint_values,
    )
    from probes.r347_scale_stable_residual import (
        solve_scale_stable_minimum_norm_edge_residual,
    )

    from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits

    started = time.perf_counter()
    limits = FeedbackLimits()
    response = build_control_response_map(
        case["model"],
        horizon=case["base_outputs"].shape[0],
    )
    solution = solve_scale_stable_minimum_norm_edge_residual(
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


def project_oracle_diagnostic(
    case: dict[str, Any],
    worker: dict[str, Any],
) -> dict[str, Any]:
    """Project one oracle return to optimizer metadata before any stop."""

    if str(worker.get("scenario_id")) != str(case["scenario_id"]):
        raise RuntimeError("R347 oracle scenario identity mismatch")
    return {
        "scenario_id": str(case["scenario_id"]),
        "point": str(case["point"]),
        "channel": str(case["channel"]),
        "sign": str(case["sign"]),
        "worker_pid": int(worker["worker_pid"]),
        "elapsed_seconds": float(worker["elapsed_seconds"]),
        "optimizer_valid": bool(worker["optimizer_valid"]),
        "target_feasible": bool(worker["target_feasible"]),
        "feasible": bool(worker["feasible"]),
        "message": str(worker["message"]),
        "solver_iterations": int(worker["solver_iterations"]),
        "maximum_constraint_residual": float(worker["maximum_constraint_residual"]),
        "maximum_target_shortfall": float(worker["maximum_target_shortfall"]),
        "objective_value": float(worker["objective_value"]),
    }


def analyse(expected_sha256: str, *, out_dir: Path = DEFAULT_OUT) -> str:
    """Execute the one sealed, create-only R347 analysis attempt."""

    seal, seal_digest = load_seal(DEFAULT_SEAL, expected_sha256)
    if out_dir.exists():
        raise FileExistsError(f"R347 result root already exists: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=False)
    attempt_path = out_dir / "analysis_attempt.json"
    attempt_digest = _write_new_json(
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
            raise RuntimeError("R347 expected sixteen unique R345 cases")
        with ProcessPoolExecutor(max_workers=WORKERS) as executor:
            oracle = list(executor.map(_oracle_worker, cases))
            oracle_diagnostic_path = out_dir / "oracle_diagnostic.json"
            oracle_diagnostic_digest = _write_new_json(
                oracle_diagnostic_path,
                {
                    "schema_version": 1,
                    "round": ROUND_ID,
                    "created_utc": datetime.now(UTC).isoformat(),
                    "rows": [
                        project_oracle_diagnostic(case, worker)
                        for case, worker in zip(cases, oracle, strict=True)
                    ],
                    "scientific_result_authorized": False,
                    "training_authorized": False,
                },
            )
            if not all(row["optimizer_valid"] for row in oracle):
                raise RuntimeError("one or more R347 oracle optimizers were not valid")
            proposals = r345._local_proposals(cases, oracle)
            local = list(executor.map(r345._local_worker, zip(cases, proposals, strict=True)))
        if not all(row["feasible"] for row in local):
            raise RuntimeError("one or more R347 local projections were not valid")
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
        analysis_digest = _write_new_json(
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
        manifest_digest = _write_new_json(
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
            _write_new_json(
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
