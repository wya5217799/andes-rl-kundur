"""Seal and run the metadata-only R346 diagnosis of the R345 invalidity."""

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

ROUND_ID = "R346"
QUESTION_ID = "Q-0091"
PARENT_ROUND = "R345"
WORKERS = 16
DEFAULT_SEAL = ROOT / "memory/rounds/R346/diagnostic_seal.json"
DEFAULT_OUT = ROOT / "results/r346_r345_optimizer_diagnosis"
PLAN = ROOT / "memory/rounds/R346/plan.md"
R345_SEAL = ROOT / "memory/rounds/R345/analysis_seal.json"
R345_ATTEMPT = ROOT / "results/r345_residual_headroom/analysis_attempt.json"
R345_FAILURE = ROOT / "results/r345_residual_headroom/failure.json"
EXPECTED_FROZEN_INPUTS = {
    "memory/rounds/R345/analysis_seal.json": (
        "47f1b287316f1475725a2c844f470016058ec06f5759d1d743829c74afbc04f4"
    ),
    "results/r345_residual_headroom/analysis_attempt.json": (
        "c93466515c681812164b4a3b3a7a1f79ba86592e0b5f83a15f5130368dcc908d"
    ),
    "results/r345_residual_headroom/failure.json": (
        "8a519fb736151ea793f18cff2b0d08de65d810dd8f49425104cd9f68de08c9a3"
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
    sidecar = Path(f"{path}.sha256")
    recorded = sidecar.read_text(encoding="ascii").split()[0]
    actual = _sha256_file(path)
    if recorded != actual:
        raise RuntimeError(f"sidecar mismatch: {path}")


def build_contract() -> dict[str, Any]:
    """Return the frozen R346 metadata-only diagnostic contract."""

    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "parent_round": PARENT_ROUND,
        "stage": "sealed-r345-optimizer-invalidity-localization",
        "scenario_count": 16,
        "unchanged_worker": "scripts.run_r345_residual_headroom._oracle_worker",
        "diagnostic_only": True,
        "serialized_fields": [
            "scenario_id",
            "point",
            "channel",
            "sign",
            "worker_pid",
            "elapsed_seconds",
            "worker_exception",
            "optimizer_valid",
            "target_feasible",
            "feasible",
            "message",
            "solver_iterations",
            "maximum_constraint_residual",
            "maximum_target_shortfall",
            "objective_value",
        ],
        "omitted_fields": [
            "base_endpoints",
            "zero_control_endpoints",
            "nominal_endpoints",
            "mismatch_bounded_endpoints",
            "edge_actions",
            "residual_node_actions",
            "counterfactual_node_commands",
            "counterfactual_soc",
        ],
        "execution": {
            "worker_processes": WORKERS,
            "native_threads_per_process": 1,
            "create_only": True,
            "retry_authorized": False,
        },
        "authorizations": {
            "scientific_result_authorized": False,
            "question_disposition_authorized": False,
            "residual_probe_authorized": False,
            "training_authorized": False,
            "distributed_runtime_authorized": False,
            "eval_authorized": False,
        },
    }


def _verify_frozen_inputs() -> None:
    for relative, expected in EXPECTED_FROZEN_INPUTS.items():
        actual = _sha256_file(ROOT / relative)
        if actual != expected:
            raise RuntimeError(f"frozen R345 input drift: {relative}: {actual}")
    for path in (R345_SEAL, R345_ATTEMPT, R345_FAILURE):
        _verify_sidecar(path)

    seal = _read_json(R345_SEAL)
    if seal.get("round") != PARENT_ROUND or seal.get("question") != QUESTION_ID:
        raise RuntimeError("R345 seal identity drift")
    sources = seal.get("sources")
    if not isinstance(sources, dict):
        raise RuntimeError("R345 seal source inventory is missing")
    for key in REUSED_R345_SOURCE_KEYS:
        source = sources.get(key)
        if not isinstance(source, dict):
            raise RuntimeError(f"R345 seal source is missing: {key}")
        path = ROOT / str(source.get("path"))
        if _sha256_file(path) != source.get("sha256"):
            raise RuntimeError(f"R345 sealed source drift: {key}")

    attempt = _read_json(R345_ATTEMPT)
    failure = _read_json(R345_FAILURE)
    if (
        attempt.get("round") != PARENT_ROUND
        or attempt.get("retry_authorized") is not False
        or failure.get("classification") != "ANALYSIS-INVALID"
        or failure.get("retry_authorized") is not False
        or failure.get("seal_sha256")
        != EXPECTED_FROZEN_INPUTS["memory/rounds/R345/analysis_seal.json"]
    ):
        raise RuntimeError("R345 attempt or failure identity drift")


def _seal_sources() -> dict[str, dict[str, str]]:
    paths = {
        "plan": PLAN,
        "adapter": Path(__file__).resolve(),
        "tests": ROOT / "tests/test_r346_r345_optimizer_diagnosis.py",
        "r345_seal": R345_SEAL,
        "r345_attempt": R345_ATTEMPT,
        "r345_failure": R345_FAILURE,
        "r345_adapter": ROOT / "scripts/run_r345_residual_headroom.py",
        "r345_probe": ROOT / "probes/r345_residual_headroom.py",
        "r345_tests": ROOT / "tests/test_r345_residual_headroom.py",
    }
    return {name: _source(path) for name, path in paths.items()}


def prepare(seal_path: Path = DEFAULT_SEAL) -> str:
    """Create the R346 source-bound diagnostic seal."""

    _verify_frozen_inputs()
    if seal_path.exists():
        raise FileExistsError(f"R346 seal already exists: {seal_path}")
    if DEFAULT_OUT.exists():
        raise FileExistsError(f"R346 result root already exists: {DEFAULT_OUT}")
    plan_text = PLAN.read_text(encoding="utf-8")
    if "state: active" not in plan_text or "Q-0091" not in plan_text:
        raise RuntimeError("R346 active plan identity is missing")
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
    """Verify the exact R346 seal and its frozen source closure."""

    payload = _read_json(path)
    actual = _sha256_file(path)
    if actual != expected_sha256:
        raise RuntimeError(f"R346 seal digest mismatch: {actual}")
    contract = payload.get("contract")
    if (
        payload.get("round") != ROUND_ID
        or payload.get("question") != QUESTION_ID
        or contract != build_contract()
        or payload.get("contract_payload_sha256") != _payload_sha256(contract)
    ):
        raise RuntimeError("R346 seal contract drift")
    if payload.get("sources") != _seal_sources():
        raise RuntimeError("R346 sealed source drift")
    _verify_frozen_inputs()
    return payload, actual


def _diagnose_worker(case: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        return r345._oracle_worker(case)
    except Exception as error:
        return {
            "scenario_id": str(case.get("scenario_id")),
            "worker_pid": os.getpid(),
            "elapsed_seconds": time.perf_counter() - started,
            "worker_exception": True,
            "exception_type": type(error).__name__,
            "message": str(error),
        }


def project_diagnostic_row(
    case: dict[str, Any],
    worker: dict[str, Any],
) -> dict[str, Any]:
    """Project one worker return to the frozen optimizer-metadata schema."""

    identity = {
        "scenario_id": str(case["scenario_id"]),
        "point": str(case["point"]),
        "channel": str(case["channel"]),
        "sign": str(case["sign"]),
        "worker_pid": int(worker["worker_pid"]),
        "elapsed_seconds": float(worker["elapsed_seconds"]),
    }
    if worker.get("worker_exception") is True:
        return {
            **identity,
            "worker_exception": True,
            "exception_type": str(worker.get("exception_type", "Exception")),
            "optimizer_valid": None,
            "target_feasible": None,
            "feasible": None,
            "message": str(worker.get("message", "")),
            "solver_iterations": None,
            "maximum_constraint_residual": None,
            "maximum_target_shortfall": None,
            "objective_value": None,
        }
    if str(worker.get("scenario_id")) != identity["scenario_id"]:
        raise RuntimeError("R346 worker scenario identity mismatch")
    return {
        **identity,
        "worker_exception": False,
        "optimizer_valid": bool(worker["optimizer_valid"]),
        "target_feasible": bool(worker["target_feasible"]),
        "feasible": bool(worker["feasible"]),
        "message": str(worker["message"]),
        "solver_iterations": int(worker["solver_iterations"]),
        "maximum_constraint_residual": float(worker["maximum_constraint_residual"]),
        "maximum_target_shortfall": float(worker["maximum_target_shortfall"]),
        "objective_value": float(worker["objective_value"]),
    }


def classify_diagnostic_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Classify only the numerical stage that invalidated R345."""

    if not rows:
        raise ValueError("R346 diagnostic rows must not be empty")
    if any(row.get("worker_exception") is True for row in rows):
        classification = "WORKER-EXCEPTION"
    elif any(
        row.get("optimizer_valid") is False and row.get("target_feasible") is False for row in rows
    ):
        classification = "RELAXATION-INVALID"
    elif any(
        row.get("optimizer_valid") is False and row.get("target_feasible") is True for row in rows
    ):
        classification = "MINIMUM-NORM-INVALID"
    else:
        classification = "NONREPRODUCIBLE-OPTIMIZER-INVALIDITY"
    invalid_scenarios = [
        str(row.get("scenario_id", "unknown"))
        for row in rows
        if row.get("worker_exception") is True or row.get("optimizer_valid") is False
    ]
    return {
        "classification": classification,
        "invalid_scenarios": invalid_scenarios,
        "scientific_result_authorized": False,
        "question_disposition_authorized": False,
        "residual_probe_authorized": False,
        "training_authorized": False,
        "distributed_runtime_authorized": False,
        "eval_authorized": False,
    }


def diagnose(expected_sha256: str, *, out_dir: Path = DEFAULT_OUT) -> str:
    """Run the one sealed metadata-only R346 diagnostic attempt."""

    seal, seal_digest = load_seal(DEFAULT_SEAL, expected_sha256)
    if out_dir.exists():
        raise FileExistsError(f"R346 result root already exists: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=False)
    attempt_path = out_dir / "diagnostic_attempt.json"
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
            "scientific_analysis_executed": False,
            "andes_executed": False,
            "training_executed": False,
            "eval_executed": False,
        },
    )
    started = time.perf_counter()
    try:
        cases = r345._load_cases()
        if len(cases) != 16 or len({case["scenario_id"] for case in cases}) != 16:
            raise RuntimeError("R346 expected exactly sixteen unique R345 cases")
        with ProcessPoolExecutor(max_workers=WORKERS) as executor:
            workers = list(executor.map(_diagnose_worker, cases))
        rows = [
            project_diagnostic_row(case, worker)
            for case, worker in zip(cases, workers, strict=True)
        ]
        decision = classify_diagnostic_rows(rows)
        diagnostic_path = out_dir / "diagnostic.json"
        diagnostic_digest = _write_new_json(
            diagnostic_path,
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "created_utc": datetime.now(UTC).isoformat(),
                "seal_sha256": seal_digest,
                "contract_payload_sha256": seal["contract_payload_sha256"],
                "diagnostic_attempt_sha256": attempt_digest,
                "elapsed_seconds": time.perf_counter() - started,
                "worker_processes": WORKERS,
                "unique_worker_pids": len({row["worker_pid"] for row in rows}),
                "row_count": len(rows),
                "rows": rows,
                **decision,
                "scientific_analysis_executed": False,
                "local_reconstruction_executed": False,
                "statistical_gate_executed": False,
                "andes_executed": False,
                "training_executed": False,
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
                        "path": diagnostic_path.relative_to(ROOT).as_posix(),
                        "sha256": diagnostic_digest,
                    },
                ],
            },
        )
        print(f"classification={decision['classification']}", flush=True)
        print(f"diagnostic_sha256={diagnostic_digest}", flush=True)
        print(f"manifest_sha256={manifest_digest}", flush=True)
        return diagnostic_digest
    except Exception as error:
        failure_path = out_dir / "failure.json"
        if not failure_path.exists():
            _write_new_json(
                failure_path,
                {
                    "schema_version": 1,
                    "round": ROUND_ID,
                    "question": QUESTION_ID,
                    "classification": "DIAGNOSTIC-INVALID",
                    "created_utc": datetime.now(UTC).isoformat(),
                    "seal_sha256": seal_digest,
                    "diagnostic_attempt_sha256": attempt_digest,
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "retry_authorized": False,
                    "scientific_result_authorized": False,
                    "training_authorized": False,
                },
            )
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    diagnose_parser = subparsers.add_parser("diagnose")
    diagnose_parser.add_argument("--expected-sha256", required=True)
    diagnose_parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "prepare":
        print(prepare(args.seal), flush=True)
        return 0
    if args.command == "diagnose":
        diagnose(args.expected_sha256, out_dir=args.out)
        return 0
    raise AssertionError(f"unexpected command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
