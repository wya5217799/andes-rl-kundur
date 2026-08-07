#!/usr/bin/env python3
"""R343 create-only recovery for the R342 formal-manifest schema mismatch.

The adapter reuses the immutable R342 training and controller-blind bank.  It
creates a successor seal in the exact schema consumed by the inherited formal
worker verifier; it never edits or retries the R342 attempt.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import time
import traceback
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


THREAD_ENVIRONMENT = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
)
for _thread_variable in THREAD_ENVIRONMENT:
    os.environ[_thread_variable] = "1"

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from scripts import run_r342_limited_reverse_residual as parent  # noqa: E402


ROUND_ID = "R343"
PHASE = "limited-reversal-formal-manifest-recovery"
EXPERIMENT = "r343_limited_reverse_recovery"
ROUND_DIR = ROOT / "memory/rounds/R343"
FORMAL_SEAL = ROUND_DIR / "formal_seal.json"
FORMAL_OUT = ROOT / "results/r343_formal_evaluation"
R342_FORMAL_SEAL = ROOT / "memory/rounds/R342/formal_seal.json"
R342_FAILURE = ROOT / "memory/rounds/R342/formal_failure.json"
REHEARSAL_RECORD = ROUND_DIR / "rehearsal.json"
FORMAL_ATTEMPT = ROUND_DIR / "formal_attempt.json"
FORMAL_FAILURE = ROUND_DIR / "formal_failure.json"
CANARY_READY_RECORD = ROUND_DIR / "canary_ready.json"
EXECUTION_RECORD = ROUND_DIR / "execution_complete.json"
CANARY_OUT = ROOT / "results/r343_physical_canary"
CANARY_TRACE_DIR = CANARY_OUT / "traces"
CANARY_LOG_DIR = CANARY_OUT / "logs"
CANARY_GATE = CANARY_OUT / "canary_gate.json"
CANARY_BARRIER_DIR = CANARY_OUT / "barrier"
FORMAL_LOG_DIR = ROOT / "results/r343_formal_logs"
_PARENT_CONFIGURED_FORMAL = parent._configured_formal


def _parent_paths() -> dict[str, Path]:
    return {
        "r342_formal_seal": R342_FORMAL_SEAL,
        "r342_failure": R342_FAILURE,
        "r342_training_summary": (
            parent.TRAINING_OUT / "training_matrix_summary.json"
        ),
        "r342_screen_summary": parent.FRESH_OUT / "screen_summary.json",
        "r342_formal_bank": parent.FRESH_OUT / "formal_bank.json",
    }


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROUND_DIR / "plan.md",
        "capacity": ROUND_DIR / "host_capacity.json",
        "r343_adapter": Path(__file__).resolve(),
        "r343_tests": ROOT / "tests/test_r343_limited_reverse_recovery.py",
        "r342_adapter": ROOT / "scripts/run_r342_limited_reverse_residual.py",
        "inherited_formal_core": ROOT / "scripts/run_r293_formal.py",
        "parent_formal_seal": R342_FORMAL_SEAL,
        "parent_failure": R342_FAILURE,
        "training_summary": parent.TRAINING_OUT / "training_matrix_summary.json",
        "screen_summary": parent.FRESH_OUT / "screen_summary.json",
        "screen_contract": parent.FRESH_OUT / "feasibility_screen_contract.json",
        "screen_provenance": parent.FRESH_OUT / "provenance.json",
        "formal_bank": parent.FRESH_OUT / "formal_bank.json",
    }


def _seal_source_paths() -> dict[str, Path]:
    paths = _source_paths()
    if REHEARSAL_RECORD.is_file():
        paths["rehearsal_record"] = REHEARSAL_RECORD
    return paths


@contextmanager
def _configured_formal() -> Iterator[Any]:
    """Expose the R342 formal core with only successor provenance rerouted."""

    with _PARENT_CONFIGURED_FORMAL() as formal:
        replacements = {
            "ROUND_ID": ROUND_ID,
            "PHASE": PHASE,
            "EXPERIMENT": EXPERIMENT,
            "DEFAULT_SEAL": FORMAL_SEAL,
            "DEFAULT_OUT": FORMAL_OUT,
        }
        previous = {name: getattr(formal, name) for name in replacements}
        for name, value in replacements.items():
            setattr(formal, name, value)
        try:
            yield formal
        finally:
            for name, value in previous.items():
                setattr(formal, name, value)


def prepare_formal_seal(
    manifest_path: Path = FORMAL_SEAL,
    out_dir: Path = FORMAL_OUT,
) -> str:
    """Create an R343 seal whose schema round-trips through worker verify."""

    if manifest_path.exists():
        raise FileExistsError(f"formal seal already exists: {manifest_path}")
    trace_dir = out_dir / "traces"
    if trace_dir.exists() and any(trace_dir.glob("*.json")):
        raise ValueError("R343 seal must precede every formal trace")

    parent_manifest = parent._load_hashed_json(R342_FORMAL_SEAL)
    parent_failure = parent._load_hashed_json(R342_FAILURE)
    if parent_failure.get("phase") != "training-through-canary-failure":
        raise ValueError("R343 parent failure identity drift")

    with _configured_formal() as formal:
        training = formal._load_json(formal.TRAINING_SUMMARY)
        screen = formal._load_json(formal.SCREEN_SUMMARY)
        formal._verify_upstreams(training, screen)
        formal.load_scenario_bank(
            formal.FORMAL_BANK,
            expected_sha256=parent_manifest["formal_bank"]["sha256"],
        )
        sources = {
            name: {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": formal.sha256_file(path),
            }
            for name, path in _seal_source_paths().items()
        }
        payload = {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": parent_manifest.get("question"),
            "phase": PHASE,
            "repository_head": formal._git_head(),
            "formal_bank": parent_manifest["formal_bank"],
            "screen": parent_manifest["screen"],
            "training_summary_sha256": formal.sha256_file(
                formal.TRAINING_SUMMARY
            ),
            "training": parent_manifest["training"],
            "mechanism": parent_manifest["mechanism"],
            "arms": parent_manifest["arms"],
            "execution": parent_manifest["execution"],
            "statistics": parent_manifest["statistics"],
            "guards": parent_manifest["guards"],
            "recovery": {
                "parent_round": "R342",
                "parent_formal_seal_sha256": formal.sha256_file(
                    R342_FORMAL_SEAL
                ),
                "parent_failure_sha256": formal.sha256_file(R342_FAILURE),
                "retraining": False,
                "bank_redraw": False,
                "threshold_change": False,
            },
            "sources": sources,
            "formal_trace_count_at_freeze": 0,
        }
        return formal._write_new(manifest_path, payload)


def verify_formal_seal(
    manifest_path: Path,
    expected: str,
) -> dict[str, Any]:
    """Run the exact configured worker verifier on the prepared seal."""

    with _configured_formal() as formal:
        return formal._verify(manifest_path, expected)


def _installed_andes_identity() -> dict[str, Any]:
    return parent._installed_andes_identity()


def _r343_process_count() -> int:
    if os.name == "nt":
        return 0
    count = 0
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            command = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(
                "utf-8", errors="replace"
            )
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if "python" in command and "run_r343_limited_reverse_recovery.py" in command:
            count += 1
    return count


def _formal_output_paths() -> list[Path]:
    return [
        FORMAL_SEAL,
        FORMAL_OUT,
        FORMAL_ATTEMPT,
        FORMAL_FAILURE,
        CANARY_OUT,
        CANARY_READY_RECORD,
        FORMAL_LOG_DIR,
        EXECUTION_RECORD,
    ]


def pre_attempt_checks(
    *,
    output_paths: list[Path] | None = None,
) -> dict[str, Any]:
    """Exercise the worker manifest verifier without formal output."""

    sources = parent._verified_hashes(_source_paths(), require_sidecars=False)
    parents = parent._verified_hashes(_parent_paths(), require_sidecars=True)
    installed = _installed_andes_identity()
    if not installed.get("version") or not installed.get("sources"):
        raise RuntimeError("installed ANDES package identity is incomplete")
    case = installed.get("case")
    if not isinstance(case, dict) or not case.get("sha256"):
        raise RuntimeError("installed Kundur case identity is incomplete")
    existing = [path for path in (output_paths or _formal_output_paths()) if path.exists()]
    if existing:
        rendered = ", ".join(str(path) for path in existing)
        raise FileExistsError(f"pre-existing R343 formal asset: {rendered}")
    process_count = _r343_process_count()
    if process_count > 16:
        raise RuntimeError(f"R343 WSL process budget exceeded: {process_count} > 16")
    thread_values = {name: os.environ.get(name) for name in THREAD_ENVIRONMENT}
    if set(thread_values.values()) != {"1"}:
        raise RuntimeError(f"native thread contract drift: {thread_values}")

    with tempfile.TemporaryDirectory(prefix="r343-roundtrip-", dir=Path.cwd()) as tmp:
        tmp_root = Path(tmp)
        seal = tmp_root / "formal_seal.json"
        digest = prepare_formal_seal(seal, tmp_root / "formal")
        verified = verify_formal_seal(seal, digest)
        if verified.get("round") != ROUND_ID:
            raise ValueError("R343 rehearsal manifest roundtrip drift")

    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "checks": {
            "source_hash": True,
            "parent_hash": True,
            "installed_package": True,
            "installed_case": True,
            "manifest_roundtrip": True,
            "output_absence": True,
        },
        "source_hashes": sources,
        "parent_hashes": parents,
        "installed_andes": installed,
        "wsl_python_processes": process_count,
        "native_threads_per_process": 1,
        "thread_environment": thread_values,
    }


def rehearse(
    *,
    record_path: Path = REHEARSAL_RECORD,
    output_paths: list[Path] | None = None,
) -> str:
    payload = {
        **pre_attempt_checks(output_paths=output_paths),
        "phase": "same-pre-attempt-path-rehearsal",
        "formal_attempt_created": False,
        "formal_outputs_created": False,
    }
    return parent._write_new_json(record_path, payload)


def verify_rehearsal(
    *,
    record_path: Path = REHEARSAL_RECORD,
    output_paths: list[Path] | None = None,
) -> dict[str, Any]:
    frozen = parent._load_hashed_json(record_path)
    current = pre_attempt_checks(output_paths=output_paths)
    for key in (
        "checks",
        "source_hashes",
        "parent_hashes",
        "installed_andes",
        "native_threads_per_process",
        "thread_environment",
    ):
        if current[key] != frozen.get(key):
            raise ValueError(f"R343 rehearsal drift: {key}")
    return current


def build_canary_contract() -> dict[str, Any]:
    """Freeze sixteen unique controller cells for plumbing evidence only."""

    controller_arms = parent.formal_arms()[1:]
    tasks = [
        {
            "shard_index": index,
            "scenario_index": index // len(controller_arms),
            "arm": controller_arms[index % len(controller_arms)],
        }
        for index in range(16)
    ]
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "worker_count": 16,
        "steps_per_worker": 15,
        "tasks": tasks,
        "performance_use": "forbidden",
        "automatic_formal_release": False,
    }


def _wait_for_canary_barrier(timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    while len(list(CANARY_BARRIER_DIR.glob("ready_*.marker"))) < 16:
        if time.monotonic() >= deadline:
            raise TimeoutError("sixteen R343 canary workers did not reach the barrier")
        time.sleep(0.05)


def run_canary_worker(
    manifest_path: Path,
    expected: str,
    *,
    shard_index: int,
    shard_count: int,
    barrier_timeout_seconds: float = 60.0,
) -> None:
    """Run one fixed 15-step cell solely for execution-path evidence."""

    if shard_count != 16 or not 0 <= shard_index < shard_count:
        raise ValueError("R343 canary requires exactly sixteen workers")
    task = build_canary_contract()["tasks"][shard_index]
    path = CANARY_TRACE_DIR / f"canary_{shard_index}.json"
    if path.exists():
        raise FileExistsError(f"R343 canary is create-only: {path}")

    with _configured_formal() as formal:
        manifest = formal._verify(manifest_path, expected)
        bank, _ = formal.load_scenario_bank(
            formal.FORMAL_BANK,
            expected_sha256=manifest["formal_bank"]["sha256"],
        )
        scenario = bank["scenarios"][task["scenario_index"]]
        arm = task["arm"]
        controller, controller_config = formal._make_controller(
            arm,
            manifest["arms"][arm],
        )
        CANARY_BARRIER_DIR.mkdir(parents=True, exist_ok=True)
        ready = CANARY_BARRIER_DIR / f"ready_{shard_index}.marker"
        with ready.open("x", encoding="utf-8") as handle:
            handle.write(f"{time.time_ns()}\n")
        _wait_for_canary_barrier(barrier_timeout_seconds)
        observed_workers = _r343_process_count()
        if observed_workers != 16:
            raise RuntimeError(
                f"R343 canary observed {observed_workers} workers, expected 16"
            )
        started_ns = time.time_ns()
        try:
            record = formal.run_vector_controller_scenario(
                controller,
                controller_name=arm,
                controller_config=controller_config,
                scenario_name=scenario["name"],
                delta_u=scenario["delta_u"],
                seed=formal.ENV_SEED,
                steps=15,
                phase="r343-sixteen-worker-physical-canary",
                evidence_hashes={
                    "formal_seal": expected,
                    "formal_bank": manifest["formal_bank"]["sha256"],
                },
            )
        except Exception as error:
            record = {
                "schema_version": 1,
                "controller": arm,
                "scenario": scenario["name"],
                "delta_u": dict(scenario["delta_u"]),
                "requested_steps": 15,
                "n_steps": 0,
                "tds_failed": True,
                "completed": False,
                "traces": [],
                "setup_error": {
                    "type": type(error).__name__,
                    "message": str(error),
                },
                "seed": formal.ENV_SEED,
            }
        finished_ns = time.time_ns()
        record.update(
            {
                "round": ROUND_ID,
                "question": None,
                "experiment": EXPERIMENT,
                "phase": "r343-sixteen-worker-physical-canary",
                "controller": arm,
                "formal_seal_sha256": expected,
                "formal_bank_sha256": manifest["formal_bank"]["sha256"],
                "execution_shard_index": shard_index,
                "execution_shard_count": shard_count,
                "simulation_started_ns": started_ns,
                "simulation_finished_ns": finished_ns,
                "observed_concurrent_workers": observed_workers,
                "scratch_working_directory": str(Path.cwd()),
                "performance_use": "forbidden",
            }
        )
        digest = formal._write_new(path, record)
        print(
            f"[canary {shard_index + 1:02d}/16] completed={record.get('completed')} "
            f"sha256={digest}",
            flush=True,
        )
        if not record.get("completed") or record.get("tds_failed"):
            raise RuntimeError(f"R343 canary worker failed: {shard_index}")


def _record_key(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def verify_canary(
    manifest_path: Path,
    expected: str,
    *,
    trace_dir: Path = CANARY_TRACE_DIR,
    log_dir: Path = CANARY_LOG_DIR,
    gate_path: Path = CANARY_GATE,
) -> str:
    """Accept only sixteen complete, overlapping and isolated canary cells."""

    manifest = verify_formal_seal(manifest_path, expected)
    starts: list[int] = []
    finishes: list[int] = []
    scratch_dirs: set[str] = set()
    record_hashes: dict[str, str] = {}
    for task in build_canary_contract()["tasks"]:
        index = task["shard_index"]
        path = trace_dir / f"canary_{index}.json"
        record = parent._load_hashed_json(path)
        expected_fields = {
            "round": ROUND_ID,
            "phase": "r343-sixteen-worker-physical-canary",
            "controller": task["arm"],
            "formal_seal_sha256": expected,
            "formal_bank_sha256": manifest["formal_bank"]["sha256"],
            "execution_shard_index": index,
            "execution_shard_count": 16,
            "observed_concurrent_workers": 16,
            "performance_use": "forbidden",
        }
        for key, value in expected_fields.items():
            if record.get(key) != value:
                raise ValueError(f"R343 canary provenance mismatch: {key}")
        if not record.get("completed") or record.get("tds_failed"):
            raise ValueError(f"R343 canary did not complete: {index}")
        starts.append(int(record["simulation_started_ns"]))
        finishes.append(int(record["simulation_finished_ns"]))
        scratch_dirs.add(str(record["scratch_working_directory"]))
        record_hashes[_record_key(path)] = parent._sha256_file(path)

    log_names = {path.name for path in log_dir.glob("shard_*.log")}
    expected_logs = {f"shard_{index}.log" for index in range(16)}
    if log_names != expected_logs:
        raise ValueError(f"R343 canary log set mismatch: {sorted(log_names)}")
    if len(scratch_dirs) != 16:
        raise ValueError("R343 canary scratch directories collided")
    if max(starts) >= min(finishes):
        raise ValueError("R343 canary simulations did not overlap")
    return parent._write_new_json(
        gate_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "classification": "PASS",
            "formal_seal_sha256": expected,
            "formal_bank_sha256": manifest["formal_bank"]["sha256"],
            "worker_count": 16,
            "unique_scratch_directory_count": len(scratch_dirs),
            "all_workers_overlapped": True,
            "record_hashes": dict(sorted(record_hashes.items())),
            "performance_use": "forbidden",
            "automatic_formal_release": False,
        },
    )


def _artifact_digest(path: Path) -> str:
    sidecar = path.with_name(path.name + ".sha256")
    expected = sidecar.read_text(encoding="utf-8").split()[0].lower()
    actual = parent._sha256_file(path)
    if actual != expected:
        raise ValueError(f"artifact sidecar mismatch: {path}")
    return actual


def _require_canary_pass(expected_formal_seal: str) -> None:
    gate = parent._load_hashed_json(CANARY_GATE)
    if gate.get("round") != ROUND_ID or gate.get("classification") != "PASS":
        raise ValueError("R343 formal execution requires a passing canary")
    if gate.get("formal_seal_sha256") != expected_formal_seal:
        raise ValueError("R343 canary belongs to a different formal seal")
    if gate.get("worker_count") != 16:
        raise ValueError("R343 canary worker count drift")
    if gate.get("automatic_formal_release") is not False:
        raise ValueError("R343 canary release contract drift")


def run_formal_shard(
    manifest_path: Path,
    expected: str,
    out_dir: Path,
    *,
    shard_index: int,
    shard_count: int,
) -> None:
    _require_canary_pass(expected)
    with _configured_formal() as formal:
        formal.run_shard(
            manifest_path,
            expected,
            out_dir,
            shard_index,
            shard_count,
        )


@contextmanager
def _parent_analysis_identity() -> Iterator[None]:
    previous_round = parent.ROUND_ID
    previous_configured = parent._configured_formal
    parent.ROUND_ID = ROUND_ID
    parent._configured_formal = _configured_formal
    try:
        yield
    finally:
        parent.ROUND_ID = previous_round
        parent._configured_formal = previous_configured


def analyse_formal(manifest_path: Path, expected: str, out_dir: Path) -> None:
    with _parent_analysis_identity():
        parent.analyse_formal(manifest_path, expected, out_dir)


def _run_wsl_stage(*stage_args: str) -> None:
    if os.name != "nt":
        raise RuntimeError("R343 host orchestration must run from Windows")
    from scripts import run_parallel_wsl_shards as launcher

    command = [
        "wsl.exe",
        "--cd",
        launcher._wsl_path(ROOT),
        launcher.WSL_PYTHON,
        launcher.SCRATCH_LAUNCHER,
        "scripts/run_r343_limited_reverse_recovery.py",
        *stage_args,
    ]
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"R343 WSL stage failed ({completed.returncode}): {' '.join(stage_args)}"
        )


def _run_host_shards(
    *,
    command: str,
    global_task_count: int,
    log_dir: Path,
    trace_dir: Path,
    worker_args: list[str],
) -> None:
    launcher = ROOT / "scripts/run_parallel_wsl_shards.py"
    argv = [
        sys.executable,
        str(launcher),
        "--worker-script",
        "scripts/run_r343_limited_reverse_recovery.py",
        "--shard-count",
        "16",
        "--process-budget",
        "16",
        "--global-task-count",
        str(global_task_count),
        "--log-dir",
        str(log_dir),
        "--trace-dir",
        str(trace_dir),
        "--",
        command,
        *worker_args,
    ]
    completed = subprocess.run(argv, cwd=ROOT, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"R343 parallel stage failed ({completed.returncode}): {command}"
        )


def _record_failure(phase: str, error: BaseException, attempt_digest: str) -> None:
    if FORMAL_FAILURE.exists():
        return
    parent._write_new_json(
        FORMAL_FAILURE,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "phase": phase,
            "attempt_sha256": attempt_digest,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
            "automatic_retry": False,
        },
    )


def execute_canary() -> str:
    """Create the successor seal, run sixteen canaries, and stop."""

    if os.name != "nt":
        raise RuntimeError("R343 canary execution must launch from Windows")
    _run_wsl_stage("verify-rehearsal")
    attempt_digest = parent._write_new_json(
        FORMAL_ATTEMPT,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "phase": "manifest-recovery-canary-attempt",
            "attempt_number": 1,
            "retraining": False,
            "bank_redraw": False,
            "automatic_retry": False,
            "automatic_formal_release": False,
        },
    )
    try:
        _run_wsl_stage("prepare-formal")
        formal_digest = _artifact_digest(FORMAL_SEAL)
        _run_wsl_stage(
            "verify-formal",
            "--expected-manifest-sha256",
            formal_digest,
        )
        _run_host_shards(
            command="canary-worker",
            global_task_count=16,
            log_dir=CANARY_LOG_DIR,
            trace_dir=CANARY_TRACE_DIR,
            worker_args=["--expected-manifest-sha256", formal_digest],
        )
        _run_wsl_stage("verify-canary", "--expected-manifest-sha256", formal_digest)
        return parent._write_new_json(
            CANARY_READY_RECORD,
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "phase": "physical-canary-ready",
                "attempt_sha256": attempt_digest,
                "formal_seal_sha256": formal_digest,
                "canary_gate_sha256": _artifact_digest(CANARY_GATE),
                "automatic_formal_release": False,
            },
        )
    except BaseException as error:
        _record_failure("manifest-recovery-canary-failure", error, attempt_digest)
        raise


def execute_formal() -> str:
    """Explicitly release the unchanged 264-trajectory formal matrix."""

    if os.name != "nt":
        raise RuntimeError("R343 formal execution must launch from Windows")
    if FORMAL_FAILURE.exists():
        raise RuntimeError("R343 has a recorded failure; retry is forbidden")
    formal_digest = _artifact_digest(FORMAL_SEAL)
    _require_canary_pass(formal_digest)
    attempt_digest = _artifact_digest(FORMAL_ATTEMPT)
    try:
        _run_host_shards(
            command="formal-worker",
            global_task_count=264,
            log_dir=FORMAL_LOG_DIR,
            trace_dir=FORMAL_OUT / "traces",
            worker_args=["--expected-manifest-sha256", formal_digest],
        )
        _run_wsl_stage("analyse-formal", "--expected-manifest-sha256", formal_digest)
        return parent._write_new_json(
            EXECUTION_RECORD,
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "phase": "formal-execution-complete",
                "formal_seal_sha256": formal_digest,
                "canary_gate_sha256": _artifact_digest(CANARY_GATE),
                "formal_summary_sha256": _artifact_digest(
                    FORMAL_OUT / "formal_summary.json"
                ),
                "automatic_retry": False,
            },
        )
    except BaseException as error:
        _record_failure("formal-execution-failure", error, attempt_digest)
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("rehearse")
    subparsers.add_parser("verify-rehearsal")
    subparsers.add_parser("prepare-formal")
    formal_verify = subparsers.add_parser("verify-formal")
    formal_verify.add_argument("--manifest", type=Path, default=FORMAL_SEAL)
    formal_verify.add_argument("--expected-manifest-sha256", required=True)
    canary_worker = subparsers.add_parser("canary-worker")
    canary_worker.add_argument("--manifest", type=Path, default=FORMAL_SEAL)
    canary_worker.add_argument("--expected-manifest-sha256", required=True)
    canary_worker.add_argument("--shard-index", type=int, required=True)
    canary_worker.add_argument("--shard-count", type=int, required=True)
    canary_verify = subparsers.add_parser("verify-canary")
    canary_verify.add_argument("--manifest", type=Path, default=FORMAL_SEAL)
    canary_verify.add_argument("--expected-manifest-sha256", required=True)
    formal_worker = subparsers.add_parser("formal-worker")
    formal_worker.add_argument("--manifest", type=Path, default=FORMAL_SEAL)
    formal_worker.add_argument("--expected-manifest-sha256", required=True)
    formal_worker.add_argument("--out-dir", type=Path, default=FORMAL_OUT)
    formal_worker.add_argument("--shard-index", type=int, required=True)
    formal_worker.add_argument("--shard-count", type=int, required=True)
    formal_analyse = subparsers.add_parser("analyse-formal")
    formal_analyse.add_argument("--manifest", type=Path, default=FORMAL_SEAL)
    formal_analyse.add_argument("--expected-manifest-sha256", required=True)
    formal_analyse.add_argument("--out-dir", type=Path, default=FORMAL_OUT)
    subparsers.add_parser("execute-canary")
    subparsers.add_parser("execute-formal")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "rehearse":
        digest = rehearse()
        print(f"[rehearsed] sha256={digest}", flush=True)
    elif args.command == "verify-rehearsal":
        verify_rehearsal()
        print("[rehearsal-verified]", flush=True)
    elif args.command == "prepare-formal":
        digest = prepare_formal_seal()
        print(f"[sealed] {FORMAL_SEAL} sha256={digest}", flush=True)
    elif args.command == "verify-formal":
        verify_formal_seal(args.manifest, args.expected_manifest_sha256)
        print("[formal-seal-verified]", flush=True)
    elif args.command == "canary-worker":
        run_canary_worker(
            args.manifest,
            args.expected_manifest_sha256,
            shard_index=args.shard_index,
            shard_count=args.shard_count,
        )
    elif args.command == "verify-canary":
        digest = verify_canary(args.manifest, args.expected_manifest_sha256)
        print(f"[physical-canary-pass] sha256={digest}", flush=True)
    elif args.command == "formal-worker":
        run_formal_shard(
            args.manifest,
            args.expected_manifest_sha256,
            args.out_dir,
            shard_index=args.shard_index,
            shard_count=args.shard_count,
        )
    elif args.command == "analyse-formal":
        analyse_formal(
            args.manifest,
            args.expected_manifest_sha256,
            args.out_dir,
        )
    elif args.command == "execute-canary":
        digest = execute_canary()
        print(f"[physical-canary-ready] sha256={digest}", flush=True)
    else:
        digest = execute_formal()
        print(f"[formal-execution-complete] sha256={digest}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
