#!/usr/bin/env python3
"""R342 staged entry for the single-point limited-reversal residual test.

This adapter keeps the reusable R293 trainer as the implementation authority,
changes its round routing to R342, selects only the distributed architecture,
and freezes ``reverse_limit=0.1``.  It exposes create-only seals and three
manual release boundaries: five-way training smoke, training through the
sixteen-way physical canary, and the final formal matrix.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import traceback
from contextlib import contextmanager
from pathlib import Path
from statistics import fmean
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

from andes_rl_kundur.control.classical_edge_residual import (  # noqa: E402
    ClassicalEdgeContract,
)


ROUND_ID = "R342"
QUESTION_ID = None
TITLE = (
    "Decoupling-Oriented Coordination of Paralleled VSGs With "
    "Multi-Agent Reinforcement Learning"
)
SEEDS = (421, 463, 509, 557, 601)
BETA_ZERO = 0.0
BETA_CANDIDATE = 0.1
RESIDUAL_SCALE = 0.5
FRESH_BANK_SEED = 2026080601
FRESH_SHARD_COUNT = 16
FORMAL_SHARD_COUNT = 16
BOOTSTRAP_SEED = 2026080602
PRIMARY_ENDPOINTS = (
    "normalized_sync_loss_hz2",
    "fast_inter_area_iae_hz_s",
)
TRAINING_SEAL = ROOT / "memory/rounds/R342/training_seal.json"
TRAINING_OUT = ROOT / "results/r342_limited_reverse_training"
REHEARSAL_RECORD = ROOT / "memory/rounds/R342/rehearsal_v2.json"
FRESH_SEAL = ROOT / "memory/rounds/R342/fresh_bank_seal.json"
FRESH_OUT = ROOT / "results/r342_fresh_bank"
FORMAL_SEAL = ROOT / "memory/rounds/R342/formal_seal.json"
FORMAL_OUT = ROOT / "results/r342_formal_evaluation"
FORMAL_ATTEMPT = ROOT / "memory/rounds/R342/formal_attempt.json"
FORMAL_FAILURE = ROOT / "memory/rounds/R342/formal_failure.json"
CANARY_OUT = ROOT / "results/r342_physical_canary"
CANARY_TRACE_DIR = CANARY_OUT / "traces"
CANARY_BARRIER_DIR = CANARY_OUT / "barrier"
CANARY_LOG_DIR = CANARY_OUT / "logs"
CANARY_GATE = CANARY_OUT / "canary_gate.json"
FORMAL_LOG_DIR = ROOT / "results/r342_formal_logs"
TRAINING_LOG_DIR = ROOT / "results/r342_training_logs"
FRESH_LOG_DIR = ROOT / "results/r342_fresh_logs"
CANARY_READY_RECORD = ROOT / "memory/rounds/R342/canary_ready.json"
SMOKE_READY_RECORD = ROOT / "memory/rounds/R342/smoke_ready.json"
EXECUTION_RECORD = ROOT / "memory/rounds/R342/execution_complete.json"
R293_GUARD_SUMMARY = (
    ROOT / "results/r293_classical_guard/classical_guard_summary.json"
)
R293_GUARD_PROVENANCE = ROOT / "results/r293_classical_guard/provenance.json"
R337_TRAINING_SUMMARY = (
    ROOT / "results/r337_prior_residual_training/training_matrix_summary.json"
)


def build_contract() -> dict[str, Any]:
    """Return the outcome-independent R342 mechanism and budget contract."""

    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "title": TITLE,
        "title_changed": False,
        "beta_zero": BETA_ZERO,
        "beta_candidate": BETA_CANDIDATE,
        "residual_scale": RESIDUAL_SCALE,
        "seeds": list(SEEDS),
        "episodes_per_seed": 300,
        "steps_per_episode": 15,
        "new_training_steps": len(SEEDS) * 300 * 15,
        "architecture": "distributed_prior",
        "beta_sweep": False,
        "automatic_retry": False,
    }


def build_fresh_bank_contract() -> dict[str, Any]:
    """Return the controller-blind single-draw bank contract."""

    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "candidate_seed": FRESH_BANK_SEED,
        "scenario_count": 24,
        "shard_count": FRESH_SHARD_COUNT,
        "redraw_after_failure": False,
        "controller": "q0",
        "formal_controller_outcomes_visible_at_freeze": False,
    }


def formal_arms() -> list[str]:
    return [
        "q0",
        "classical_edge",
        *(f"beta0_s{seed}" for seed in SEEDS),
        *(f"beta0p1_s{seed}" for seed in SEEDS),
    ]


def build_formal_contract() -> dict[str, Any]:
    arms = formal_arms()
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "arms": arms,
        "arm_count": len(arms),
        "new_controller_trajectory_budget": (len(arms) - 1) * 24,
        "reused_q0_trajectory_count": 24,
        "total_matrix_count": len(arms) * 24,
        "shard_count": FORMAL_SHARD_COUNT,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "automatic_retry": False,
    }


def build_physical_canary_contract() -> dict[str, Any]:
    controller_arms = formal_arms()[1:]
    tasks = [
        {
            "shard_index": index,
            "scenario_index": index // len(controller_arms),
            "arm": controller_arms[index % len(controller_arms)],
        }
        for index in range(FORMAL_SHARD_COUNT)
    ]
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "worker_count": FORMAL_SHARD_COUNT,
        "steps_per_worker": 15,
        "task_count": len(tasks),
        "tasks": tasks,
        "performance_use": "forbidden",
        "automatic_formal_release": False,
    }


def build_execution_stage_plan() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "stages": [
            {"name": "training-smoke", "workers": 5},
            {"name": "full-training", "workers": 5},
            {"name": "fresh-bank-screen", "workers": 16},
            {"name": "physical-canary", "workers": 16},
        ],
        "release_points": ["training-smoke", "physical-canary"],
        "initial_stop_after": "training-smoke",
        "automatic_full_training_release": False,
        "automatic_formal_release": False,
        "full_formal_workers_after_release": 16,
    }


def training_jobs() -> list[dict[str, Any]]:
    """Return exactly one single-threaded training job for every frozen seed."""

    return [
        {
            "architecture": "distributed_prior",
            "seed": seed,
            "native_threads": 1,
        }
        for seed in SEEDS
    ]


def training_job_for_shard(shard_index: int, shard_count: int) -> dict[str, Any]:
    """Bind one and only one frozen seed to each of five training workers."""

    jobs = training_jobs()
    if shard_count != len(jobs):
        raise ValueError("R342 training requires exactly five shards")
    if not 0 <= shard_index < shard_count:
        raise ValueError("training shard index is outside the frozen matrix")
    return jobs[shard_index]


def _selected_contract() -> ClassicalEdgeContract:
    from scripts import train_r293_prior_residual as training

    guard = training._load_json(R293_GUARD_SUMMARY)
    if guard.get("classification") != "CLASSICAL-GUARD-PASS":
        raise ValueError("R293 selected classical guard did not pass")
    parent = training._contract_from_telemetry(
        guard["selected_classical_contract"]
    )
    if parent.name != "classical_edge_full_k1":
        raise ValueError(f"selected classical parent drift: {parent.name}")
    return ClassicalEdgeContract(
        family=parent.family,
        gain=parent.gain,
        residual_scale=RESIDUAL_SCALE,
        reverse_limit=BETA_CANDIDATE,
    )


def _training_source_paths() -> dict[str, Path]:
    paths = {
        "plan": ROOT / "memory/rounds/R342/plan.md",
        "capacity": ROOT / "memory/rounds/R342/host_capacity.json",
        "r342_adapter": Path(__file__).resolve(),
        "r342_tests": ROOT / "tests/test_r342_limited_reverse_residual.py",
        "design_record": ROOT
        / "paper/icems2026/working/gpt_pro_minimal_change_algorithm_optimization.md",
        "inherited_training": ROOT / "scripts/train_r293_prior_residual.py",
        "prior_agents": ROOT / "src/andes_rl_kundur/agents/classical_prior_td3.py",
        "classical_controller": ROOT
        / "src/andes_rl_kundur/control/classical_edge_residual.py",
        "parent_guard": R293_GUARD_SUMMARY,
        "parent_guard_provenance": R293_GUARD_PROVENANCE,
        "parent_beta_zero_seal": ROOT / "memory/rounds/R337/training_seal.json",
        "parent_beta_zero_summary": ROOT
        / "results/r337_prior_residual_training/training_matrix_summary.json",
    }
    if REHEARSAL_RECORD.is_file():
        paths["rehearsal_record"] = REHEARSAL_RECORD
    return paths


def _source_paths() -> dict[str, Path]:
    paths = _training_source_paths()
    # The rehearsal freezes the sources that will later consume its record;
    # hashing the not-yet-created record here would make verification self-referential.
    paths.pop("rehearsal_record", None)
    paths.update(
        {
            "parallel_launcher": ROOT / "scripts/run_parallel_wsl_shards.py",
            "parallel_launcher_tests": ROOT / "tests/test_parallel_wsl_shards.py",
            "scratch_launcher": ROOT / "scripts/andes_scratch.py",
            "vector_runner": ROOT
            / "src/andes_rl_kundur/evaluation/vector_residual.py",
            "sealed_bank": ROOT
            / "src/andes_rl_kundur/evaluation/sealed_bank.py",
        }
    )
    return paths


def _parent_paths() -> dict[str, Path]:
    return {
        "r293_guard": R293_GUARD_SUMMARY,
        "r293_guard_provenance": R293_GUARD_PROVENANCE,
        "r337_training_seal": ROOT / "memory/rounds/R337/training_seal.json",
        "r337_training_summary": ROOT
        / "results/r337_prior_residual_training/training_matrix_summary.json",
        "r338_claim": ROOT / "memory/claims/CLM-0905.md",
        "r338_feed": ROOT / "paper/icems2026/reports/R338.md",
    }


def _formal_output_paths() -> list[Path]:
    return [
        TRAINING_SEAL,
        TRAINING_OUT,
        FRESH_SEAL,
        FRESH_OUT,
        FORMAL_SEAL,
        FORMAL_OUT,
        FORMAL_ATTEMPT,
        FORMAL_FAILURE,
        CANARY_OUT,
        FORMAL_LOG_DIR,
        TRAINING_LOG_DIR,
        FRESH_LOG_DIR,
        SMOKE_READY_RECORD,
        CANARY_READY_RECORD,
        EXECUTION_RECORD,
    ]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verified_hashes(
    paths: dict[str, Path],
    *,
    require_sidecars: bool,
) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(path)
        digest = _sha256_file(path)
        if require_sidecars and path.suffix == ".json":
            sidecar = path.with_name(path.name + ".sha256")
            if not sidecar.is_file():
                raise FileNotFoundError(sidecar)
            expected = sidecar.read_text(encoding="utf-8").split()[0].lower()
            if digest != expected:
                raise ValueError(f"parent hash sidecar mismatch: {path}")
        hashes[name] = digest
    return hashes


def _installed_andes_identity() -> dict[str, Any]:
    from scripts import run_r337_icems_comparison as r337

    return r337._installed_andes_identity()


def _r342_python_process_count() -> int:
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
        if "python" in command and "run_r342_limited_reverse_residual.py" in command:
            count += 1
    return count


def pre_attempt_checks(
    *,
    output_paths: list[Path] | None = None,
) -> dict[str, Any]:
    """Run the checks shared by rehearsal and every later execution entry."""

    sources = _verified_hashes(_source_paths(), require_sidecars=False)
    parents = _verified_hashes(_parent_paths(), require_sidecars=True)
    installed = _installed_andes_identity()
    if not installed.get("version") or not installed.get("sources"):
        raise RuntimeError("installed ANDES package identity is incomplete")
    case = installed.get("case")
    if not isinstance(case, dict) or not case.get("sha256"):
        raise RuntimeError("installed Kundur case identity is incomplete")
    existing = [path for path in (output_paths or _formal_output_paths()) if path.exists()]
    if existing:
        rendered = ", ".join(str(path) for path in existing)
        raise FileExistsError(f"pre-existing R342 formal asset: {rendered}")
    process_count = _r342_python_process_count()
    if process_count > 16:
        raise RuntimeError(f"R342 WSL Python process budget exceeded: {process_count} > 16")
    thread_values = {name: os.environ.get(name) for name in THREAD_ENVIRONMENT}
    if set(thread_values.values()) != {"1"}:
        raise RuntimeError(f"native thread contract drift: {thread_values}")
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "checks": {
            "source_hash": True,
            "parent_hash": True,
            "installed_package": True,
            "installed_case": True,
            "output_absence": True,
        },
        "source_hashes": sources,
        "parent_hashes": parents,
        "installed_andes": installed,
        "wsl_python_processes": process_count,
        "native_threads_per_process": 1,
        "thread_environment": thread_values,
    }


def _canonical_json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def _write_new_json(path: Path, payload: object) -> str:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite immutable artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _canonical_json_bytes(payload)
    path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    path.with_name(path.name + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="utf-8"
    )
    return digest


def _load_hashed_json(path: Path) -> dict[str, Any]:
    sidecar = path.with_name(path.name + ".sha256")
    expected = sidecar.read_text(encoding="utf-8").split()[0].lower()
    if _sha256_file(path) != expected:
        raise ValueError(f"hash mismatch: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def rehearse(
    *,
    record_path: Path = REHEARSAL_RECORD,
    output_paths: list[Path] | None = None,
) -> str:
    """Persist a create-only rehearsal without creating experimental outputs."""

    payload = {
        **pre_attempt_checks(output_paths=output_paths),
        "phase": "same-pre-attempt-path-rehearsal",
        "formal_attempt_created": False,
        "formal_outputs_created": False,
    }
    return _write_new_json(record_path, payload)


def verify_rehearsal(
    *,
    record_path: Path = REHEARSAL_RECORD,
    output_paths: list[Path] | None = None,
) -> dict[str, Any]:
    """Rerun the same checks and reject identity or runtime drift."""

    frozen = _load_hashed_json(record_path)
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
            raise ValueError(f"rehearsal drift: {key}")
    return current


@contextmanager
def _configured_training() -> Iterator[Any]:
    from scripts import train_r293_prior_residual as training

    replacements = {
        "ROUND_ID": ROUND_ID,
        "QUESTION_ID": QUESTION_ID,
        "SEEDS": SEEDS,
        "ARCHITECTURES": ("distributed_prior",),
        "GUARD_SUMMARY": R293_GUARD_SUMMARY,
        "GUARD_PROVENANCE": R293_GUARD_PROVENANCE,
        "DEFAULT_SEAL": TRAINING_SEAL,
        "DEFAULT_OUT": TRAINING_OUT,
        "_selected_contract": _selected_contract,
        "_source_paths": _training_source_paths,
    }
    previous = {name: getattr(training, name) for name in replacements}
    for name, value in replacements.items():
        setattr(training, name, value)
    try:
        yield training
    finally:
        for name, value in previous.items():
            setattr(training, name, value)


def prepare_training_seal(
    manifest_path: Path = TRAINING_SEAL,
    out_root: Path = TRAINING_OUT,
) -> None:
    """Create the five-checkpoint R342 training seal without running ANDES."""

    with _configured_training() as training:
        training.prepare(manifest_path, out_root)


def _wait_for_training_barrier(
    barrier_dir: Path,
    *,
    shard_count: int,
    timeout_seconds: float,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while len(list(barrier_dir.glob("ready_*.marker"))) < shard_count:
        if time.monotonic() >= deadline:
            raise TimeoutError("five R342 training workers did not reach the barrier")
        time.sleep(0.05)


def run_training_worker(
    manifest_path: Path,
    expected: str,
    out_root: Path,
    *,
    shard_index: int,
    shard_count: int,
    smoke_episodes: int | None,
    barrier_dir: Path | None = None,
    barrier_timeout_seconds: float = 60.0,
) -> int:
    """Run one frozen seed and persist an outcome-independent worker receipt."""

    job = training_job_for_shard(shard_index, shard_count)
    if barrier_dir is not None:
        barrier_dir.mkdir(parents=True, exist_ok=True)
        ready = barrier_dir / f"ready_{shard_index}.marker"
        with ready.open("x", encoding="utf-8") as handle:
            handle.write(f"{time.time_ns()}\n")
        _wait_for_training_barrier(
            barrier_dir,
            shard_count=shard_count,
            timeout_seconds=barrier_timeout_seconds,
        )
    started_ns = time.time_ns()
    with _configured_training() as training:
        return_code = training.train(
            manifest_path,
            expected,
            out_root,
            job["architecture"],
            job["seed"],
            "cpu",
            smoke_episodes,
        )
    finished_ns = time.time_ns()
    receipt_dir = out_root / (
        "smoke_receipts" if smoke_episodes is not None else "training_receipts"
    )
    _write_new_json(
        receipt_dir / f"worker_{shard_index}.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "architecture": job["architecture"],
            "seed": job["seed"],
            "shard_index": shard_index,
            "shard_count": shard_count,
            "smoke_episodes": smoke_episodes,
            "started_ns": started_ns,
            "finished_ns": finished_ns,
            "return_code": return_code,
            "native_threads": 1,
            "scratch_working_directory": str(Path.cwd()),
        },
    )
    return return_code


def verify_training_smoke(out_root: Path = TRAINING_OUT) -> str:
    """Release full training only after five valid smoke workers overlapped."""

    starts: list[int] = []
    finishes: list[int] = []
    receipt_hashes: dict[str, str] = {}
    summary_hashes: dict[str, str] = {}
    for shard_index, seed in enumerate(SEEDS):
        receipt_path = out_root / "smoke_receipts" / f"worker_{shard_index}.json"
        summary_path = (
            out_root
            / "smoke"
            / f"distributed_prior_s{seed}_e1"
            / "training_summary.json"
        )
        receipt = _load_hashed_json(receipt_path)
        summary = _load_hashed_json(summary_path)
        expected_receipt = {
            "round": ROUND_ID,
            "seed": seed,
            "shard_index": shard_index,
            "shard_count": len(SEEDS),
            "smoke_episodes": 1,
            "return_code": 0,
        }
        for key, value in expected_receipt.items():
            if receipt.get(key) != value:
                raise ValueError(f"training smoke receipt mismatch: {key}")
        expected_summary = {
            "round": ROUND_ID,
            "architecture": "distributed_prior",
            "seed": seed,
            "episodes_completed": 1,
            "total_steps": 15,
            "smoke": True,
            "failed": False,
            "all_completed": True,
        }
        for key, value in expected_summary.items():
            if summary.get(key) != value:
                raise ValueError(f"training smoke summary mismatch: {key}")
        starts.append(int(receipt["started_ns"]))
        finishes.append(int(receipt["finished_ns"]))
        receipt_hashes[str(receipt_path.relative_to(out_root))] = _sha256_file(
            receipt_path
        )
        summary_hashes[str(summary_path.relative_to(out_root))] = _sha256_file(
            summary_path
        )
    if max(starts) >= min(finishes):
        raise ValueError("five R342 training workers did not overlap")
    worker_seconds = [
        (finished - started) / 1_000_000_000
        for started, finished in zip(starts, finishes, strict=True)
    ]
    maximum_worker_seconds = max(worker_seconds)
    observed_parallel_wall_seconds = (max(finishes) - min(starts)) / 1_000_000_000
    return _write_new_json(
        out_root / "smoke_gate.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "classification": "PASS",
            "worker_count": len(SEEDS),
            "all_workers_overlapped": True,
            "all_workers_completed": True,
            "performance_use": "forbidden",
            "timing": {
                "worker_seconds": worker_seconds,
                "maximum_worker_seconds": maximum_worker_seconds,
                "observed_parallel_wall_seconds": observed_parallel_wall_seconds,
                "estimated_full_training_wall_seconds": (
                    maximum_worker_seconds * build_contract()["episodes_per_seed"]
                ),
                "estimate_basis": "maximum one-episode worker time times 300",
            },
            "receipt_hashes": dict(sorted(receipt_hashes.items())),
            "summary_hashes": dict(sorted(summary_hashes.items())),
        },
    )


def _verify_r342_training(training_summary: dict[str, Any]) -> None:
    """Require the complete five-checkpoint B3 matrix before bank creation."""

    expected = {
        "round": ROUND_ID,
        "all_completed": True,
        "expected_run_count": len(SEEDS),
        "observed_run_count": len(SEEDS),
        "seed_selection_performed": False,
    }
    for key, value in expected.items():
        if training_summary.get(key) != value:
            raise ValueError("fresh bank requires five completed R342 training runs")
    for path_text, digest in training_summary.get("artifact_hashes", {}).items():
        if _sha256_file(ROOT / path_text) != digest:
            raise ValueError(f"R342 training artifact drift: {path_text}")


def _fresh_source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R342/plan.md",
        "capacity": ROOT / "memory/rounds/R342/host_capacity.json",
        "rehearsal_record": REHEARSAL_RECORD,
        "r342_adapter": Path(__file__).resolve(),
        "r342_tests": ROOT / "tests/test_r342_limited_reverse_residual.py",
        "fresh_bank_core": ROOT / "scripts/run_r292_fresh_bank.py",
        "vector_runner": ROOT
        / "src/andes_rl_kundur/evaluation/vector_residual.py",
        "q0_record_audit": ROOT
        / "src/andes_rl_kundur/evaluation/r292_screen.py",
        "q0_bank_audit": ROOT
        / "src/andes_rl_kundur/evaluation/r292_screen_bank.py",
        "prospective_authority": ROOT
        / "src/andes_rl_kundur/evaluation/prospective_authority.py",
        "sealed_bank": ROOT / "src/andes_rl_kundur/evaluation/sealed_bank.py",
        "training_summary": TRAINING_OUT / "training_matrix_summary.json",
        "training_seal": TRAINING_SEAL,
        "reference_bank": ROOT
        / "results/r274_prospective_active_power_authority/formal_bank.json",
    }


@contextmanager
def _configured_fresh() -> Iterator[Any]:
    from scripts import run_r293_fresh_bank as adapter

    fresh = adapter.CORE
    replacements = {
        "ROUND_ID": ROUND_ID,
        "QUESTION_ID": QUESTION_ID,
        "CANDIDATE_SEED": FRESH_BANK_SEED,
        "SHARD_COUNT": FRESH_SHARD_COUNT,
        "TRAINING_SUMMARY": TRAINING_OUT / "training_matrix_summary.json",
        "DEFAULT_SEAL": FRESH_SEAL,
        "DEFAULT_OUT": FRESH_OUT,
        "FORMAL_TRACE_DIR": FORMAL_OUT / "traces",
        "_verify_training": _verify_r342_training,
        "_source_paths": _fresh_source_paths,
    }
    previous = {name: getattr(fresh, name) for name in replacements}
    for name, value in replacements.items():
        setattr(fresh, name, value)
    try:
        yield fresh
    finally:
        for name, value in previous.items():
            setattr(fresh, name, value)


def prepare_fresh_bank_seal(
    manifest_path: Path = FRESH_SEAL,
    out_dir: Path = FRESH_OUT,
) -> None:
    with _configured_fresh() as fresh:
        fresh.prepare(manifest_path, out_dir)


def run_fresh_bank_shard(
    manifest_path: Path,
    expected: str,
    out_dir: Path,
    *,
    shard_index: int,
    shard_count: int,
) -> None:
    with _configured_fresh() as fresh:
        fresh.run_shard(
            manifest_path,
            expected,
            out_dir,
            shard_index,
            shard_count,
        )


def analyse_fresh_bank(
    manifest_path: Path,
    expected: str,
    out_dir: Path,
) -> None:
    with _configured_fresh() as fresh:
        fresh.analyse(manifest_path, expected, out_dir)


def _formal_checkpoint_path(learned_family: str, seed: int) -> Path:
    if learned_family == "beta0":
        root = ROOT / "results/r337_prior_residual_training"
    elif learned_family == "beta0p1":
        root = TRAINING_OUT
    else:
        raise ValueError(f"unknown learned family: {learned_family}")
    return root / f"distributed_prior_s{seed}" / "final.pt"


def _formal_controller_contract_path(learned_family: str, seed: int) -> Path:
    return _formal_checkpoint_path(learned_family, seed).with_name(
        "controller_contract.json"
    )


def _verify_r337_training(training_summary: dict[str, Any]) -> None:
    if (
        not training_summary.get("all_completed")
        or training_summary.get("observed_run_count") != 10
        or training_summary.get("seed_selection_performed") is not False
    ):
        raise ValueError("formal comparison requires the ten completed R337 runs")
    rows = training_summary.get("rows", [])
    distributed_seeds = {
        int(row["seed"])
        for row in rows
        if row.get("architecture") == "distributed_prior"
    }
    if distributed_seeds != set(SEEDS):
        raise ValueError("R337 beta-zero seed set drift")
    for path_text, digest in training_summary.get("artifact_hashes", {}).items():
        if _sha256_file(ROOT / path_text) != digest:
            raise ValueError(f"R337 training artifact drift: {path_text}")


def _verify_formal_upstreams(
    training_summary: dict[str, Any],
    screen_summary: dict[str, Any],
) -> None:
    _verify_r342_training(training_summary)
    parent = _load_hashed_json(R337_TRAINING_SUMMARY)
    _verify_r337_training(parent)
    if screen_summary.get("decision", {}).get("classification") != "PASS":
        raise ValueError("formal evaluation requires a passing fresh-bank screen")
    if screen_summary.get("controller_trace_count_at_freeze") != 0:
        raise ValueError("fresh bank was not frozen before controller traces")
    if screen_summary.get("redraw_performed") is not False:
        raise ValueError("fresh bank reports a forbidden redraw")


def _classical_beta0_contract() -> ClassicalEdgeContract:
    from scripts import train_r293_prior_residual as training

    guard = training._load_json(R293_GUARD_SUMMARY)
    parent = training._contract_from_telemetry(
        guard["selected_classical_contract"]
    )
    if parent.name != "classical_edge_full_k1":
        raise ValueError(f"selected classical parent drift: {parent.name}")
    return parent


def _formal_arm_manifest(training_summary: dict[str, Any]) -> dict[str, Any]:
    from andes_rl_kundur.evaluation.sealed_bank import sha256_file

    candidate_rows = {
        int(row["seed"]): row
        for row in training_summary["rows"]
        if row["architecture"] == "distributed_prior"
    }
    parent_summary = _load_hashed_json(R337_TRAINING_SUMMARY)
    _verify_r337_training(parent_summary)
    parent_rows = {
        int(row["seed"]): row
        for row in parent_summary["rows"]
        if row["architecture"] == "distributed_prior"
    }
    classical = _classical_beta0_contract()
    arms: dict[str, Any] = {
        "q0": {"kind": "deterministic", "controller": "q0"},
        "classical_edge": {
            "kind": "deterministic",
            "controller": classical.name,
            "contract": classical.telemetry(),
            "classical_guard_sha256": sha256_file(R293_GUARD_SUMMARY),
        },
    }
    for family, rows, training_round, question in (
        ("beta0", parent_rows, "R337", "Q-0088"),
        ("beta0p1", candidate_rows, ROUND_ID, QUESTION_ID),
    ):
        for seed in SEEDS:
            row = rows[seed]
            checkpoint = _formal_checkpoint_path(family, seed)
            contract_path = _formal_controller_contract_path(family, seed)
            if sha256_file(checkpoint) != row["checkpoint_sha256"]:
                raise ValueError(f"checkpoint drift: {checkpoint}")
            arms[f"{family}_s{seed}"] = {
                "kind": "learned",
                "architecture": "distributed_prior",
                "learned_family": family,
                "training_round": training_round,
                "question": question,
                "seed": seed,
                "checkpoint": str(checkpoint.relative_to(ROOT)).replace("\\", "/"),
                "checkpoint_sha256": row["checkpoint_sha256"],
                "controller_contract": str(contract_path.relative_to(ROOT)).replace(
                    "\\", "/"
                ),
                "controller_contract_sha256": sha256_file(contract_path),
                "actor_parameter_count": row["actor_parameter_count"],
            }
    if tuple(arms) != tuple(formal_arms()):
        raise ValueError("R342 formal arm order drift")
    return arms


def _make_r342_controller(
    arm: str,
    config: dict[str, Any],
) -> tuple[Any, dict[str, Any]]:
    from andes_rl_kundur.agents.classical_prior_td3 import (
        DistributedPriorResidualTD3,
    )
    from andes_rl_kundur.control.classical_edge_residual import (
        ClassicalEdgeController,
    )

    if arm == "classical_edge":
        classical = _classical_beta0_contract()
        return ClassicalEdgeController(classical), {
            "architecture": "classical_edge",
            "classical_contract": classical.telemetry(),
        }
    family = str(config["learned_family"])
    classical = (
        _classical_beta0_contract() if family == "beta0" else _selected_contract()
    )
    controller = DistributedPriorResidualTD3(
        classical_contract=classical,
        hidden_sizes=[64, 64],
        device="cpu",
    )
    metadata = controller.load(ROOT / config["checkpoint"])
    expected_metadata = {
        "round": config["training_round"],
        "question": config["question"],
        "architecture": "distributed_prior",
        "seed": config["seed"],
        "episodes_completed": 300,
        "total_steps": 4500,
        "smoke": False,
    }
    for key, value in expected_metadata.items():
        if metadata.get(key) != value:
            raise ValueError(f"checkpoint metadata mismatch for {arm}: {key}")
    return controller, {
        "architecture": "distributed_prior",
        "learned_family": family,
        "seed": config["seed"],
        "checkpoint": config["checkpoint"],
        "checkpoint_sha256": config["checkpoint_sha256"],
        "controller_contract_sha256": config["controller_contract_sha256"],
        "classical_contract": classical.telemetry(),
        "checkpoint_metadata": metadata,
    }


def _formal_source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R342/plan.md",
        "capacity": ROOT / "memory/rounds/R342/host_capacity.json",
        "rehearsal_record": REHEARSAL_RECORD,
        "r342_adapter": Path(__file__).resolve(),
        "r342_tests": ROOT / "tests/test_r342_limited_reverse_residual.py",
        "inherited_formal_core": ROOT / "scripts/run_r293_formal.py",
        "decision_probe": ROOT / "probes/r342_limited_reverse_decision.py",
        "decision_tests": ROOT / "tests/test_r342_limited_reverse_decision.py",
        "vector_runner": ROOT
        / "src/andes_rl_kundur/evaluation/vector_residual.py",
        "sealed_bank": ROOT / "src/andes_rl_kundur/evaluation/sealed_bank.py",
        "prior_actor": ROOT / "src/andes_rl_kundur/agents/classical_prior_td3.py",
        "classical_controller": ROOT
        / "src/andes_rl_kundur/control/classical_edge_residual.py",
        "formal_bank": FRESH_OUT / "formal_bank.json",
        "screen_summary": FRESH_OUT / "screen_summary.json",
        "screen_contract": FRESH_OUT / "feasibility_screen_contract.json",
        "screen_provenance": FRESH_OUT / "provenance.json",
        "r342_training_summary": TRAINING_OUT / "training_matrix_summary.json",
        "r337_training_summary": R337_TRAINING_SUMMARY,
        "classical_guard": R293_GUARD_SUMMARY,
    }


@contextmanager
def _configured_formal() -> Iterator[Any]:
    from scripts import run_r293_formal as formal

    arms = tuple(formal_arms())
    replacements = {
        "ROUND_ID": ROUND_ID,
        "QUESTION_ID": QUESTION_ID,
        "PHASE": "fresh-bank-limited-reversal-formal",
        "EXPERIMENT": "r342_limited_reverse_residual",
        "ALLOW_EXISTING_TRACE_RESUME": False,
        "SEEDS": SEEDS,
        "BOOTSTRAP_SEED": BOOTSTRAP_SEED,
        "SHARD_COUNT": FORMAL_SHARD_COUNT,
        "ARMS": arms,
        "NEW_TRACE_ARMS": arms[1:],
        "FRESH_DIR": FRESH_OUT,
        "FORMAL_BANK": FRESH_OUT / "formal_bank.json",
        "SCREEN_SUMMARY": FRESH_OUT / "screen_summary.json",
        "SCREEN_CONTRACT": FRESH_OUT / "feasibility_screen_contract.json",
        "SCREEN_PROVENANCE": FRESH_OUT / "provenance.json",
        "TRAINING_SUMMARY": TRAINING_OUT / "training_matrix_summary.json",
        "CLASSICAL_GUARD": R293_GUARD_SUMMARY,
        "DEFAULT_SEAL": FORMAL_SEAL,
        "DEFAULT_OUT": FORMAL_OUT,
        "_verify_upstreams": _verify_formal_upstreams,
        "_arm_manifest": _formal_arm_manifest,
        "_source_paths": _formal_source_paths,
        "_make_controller": _make_r342_controller,
    }
    previous = {name: getattr(formal, name) for name in replacements}
    for name, value in replacements.items():
        setattr(formal, name, value)
    try:
        yield formal
    finally:
        for name, value in previous.items():
            setattr(formal, name, value)


def _mechanism_engagement(
    records: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    reverse_command_count = 0
    steps_with_reverse = 0
    engaged_arms: set[str] = set()
    observed_steps = 0
    for arm, arm_records in records.items():
        if not arm.startswith("beta0p1_s"):
            continue
        for record in arm_records:
            for step in record.get("traces", []):
                composition = step.get("residual_composition")
                if not isinstance(composition, dict):
                    raise ValueError(f"missing residual composition telemetry: {arm}")
                if float(composition.get("reverse_limit", -1.0)) != BETA_CANDIDATE:
                    raise ValueError(f"reverse-limit telemetry drift: {arm}")
                count = int(composition.get("reverse_count", -1))
                if count < 0:
                    raise ValueError(f"invalid reverse count: {arm}")
                observed_steps += 1
                reverse_command_count += count
                if count > 0:
                    steps_with_reverse += 1
                    engaged_arms.add(arm)
    return {
        "candidate_step_count": observed_steps,
        "reverse_command_count": reverse_command_count,
        "steps_with_reverse": steps_with_reverse,
        "engaged_seed_count": len(engaged_arms),
        "engaged": reverse_command_count > 0,
    }


def _seed_directionality(
    grid: dict[str, dict[str, dict[str, Any]]],
    bank_names: list[str],
) -> tuple[int, int, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    for seed in SEEDS:
        versus_classical: dict[str, bool] = {}
        versus_beta0: dict[str, bool] = {}
        for endpoint in PRIMARY_ENDPOINTS:
            candidate = fmean(
                float(grid[name][f"beta0p1_s{seed}"][endpoint])
                for name in bank_names
            )
            beta_zero = fmean(
                float(grid[name][f"beta0_s{seed}"][endpoint])
                for name in bank_names
            )
            classical = fmean(
                float(grid[name]["classical_edge"][endpoint])
                for name in bank_names
            )
            versus_classical[endpoint] = candidate < classical
            versus_beta0[endpoint] = candidate < beta_zero
        rows.append(
            {
                "seed": seed,
                "candidate_vs_classical": versus_classical,
                "candidate_vs_beta0": versus_beta0,
                "both_primary_vs_classical": all(versus_classical.values()),
                "both_primary_vs_beta0": all(versus_beta0.values()),
            }
        )
    return (
        sum(row["both_primary_vs_classical"] for row in rows),
        sum(row["both_primary_vs_beta0"] for row in rows),
        rows,
    )


def prepare_formal_seal(
    manifest_path: Path = FORMAL_SEAL,
    out_dir: Path = FORMAL_OUT,
) -> None:
    """Seal the truthful beta-zero versus beta-0.1 twelve-arm comparison."""

    with _configured_formal() as formal:
        if manifest_path.exists():
            raise FileExistsError(f"formal seal already exists: {manifest_path}")
        trace_dir = out_dir / "traces"
        if trace_dir.exists() and any(trace_dir.glob("*.json")):
            raise ValueError("formal seal must precede every R342 formal trace")
        training = formal._load_json(formal.TRAINING_SUMMARY)
        screen = formal._load_json(formal.SCREEN_SUMMARY)
        _verify_formal_upstreams(training, screen)
        screen_provenance = formal._load_json(formal.SCREEN_PROVENANCE)
        for path_text, digest in screen_provenance["trace_hashes"].items():
            if formal.sha256_file(ROOT / path_text) != digest:
                raise ValueError(f"fresh-screen q0 trace drift: {path_text}")
        bank, bank_hash = formal.load_scenario_bank(
            formal.FORMAL_BANK,
            expected_sha256=screen["formal_bank_sha256"],
        )
        if bank["scenario_count"] != 24:
            raise ValueError("R342 formal bank must contain exactly 24 scenarios")
        arms = _formal_arm_manifest(training)
        sources = {
            name: {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": formal.sha256_file(path),
            }
            for name, path in _formal_source_paths().items()
        }
        contract = build_formal_contract()
        payload = {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "phase": formal.PHASE,
            "repository_head": formal._git_head(),
            "mechanism": build_contract(),
            "formal_bank": {
                "path": str(formal.FORMAL_BANK.relative_to(ROOT)).replace("\\", "/"),
                "sha256": bank_hash,
                "scenario_count": 24,
                "generator_seed": FRESH_BANK_SEED,
            },
            "screen": {
                "summary_sha256": formal.sha256_file(formal.SCREEN_SUMMARY),
                "contract_sha256": formal.sha256_file(formal.SCREEN_CONTRACT),
                "provenance_sha256": formal.sha256_file(formal.SCREEN_PROVENANCE),
                "frozen_q0_trace_hashes": screen_provenance["trace_hashes"],
                "q0_reuse_after_formal_seal": True,
                "redraw_after_failure": False,
            },
            "training": {
                "r342_summary_sha256": formal.sha256_file(formal.TRAINING_SUMMARY),
                "r337_beta_zero_summary_sha256": formal.sha256_file(
                    R337_TRAINING_SUMMARY
                ),
                "paired_seeds": list(SEEDS),
                "seed_selection": False,
            },
            "arms": arms,
            "execution": {
                "environment_seed": formal.ENV_SEED,
                "steps": formal.STEPS,
                "shard_count": FORMAL_SHARD_COUNT,
                "arm_count": contract["arm_count"],
                "new_controller_trajectory_budget": contract[
                    "new_controller_trajectory_budget"
                ],
                "reused_q0_trajectory_count": 24,
                "total_matrix_count": contract["total_matrix_count"],
                "overwrite": False,
                "retry_failed_controller_trajectory": False,
            },
            "statistics": {
                "hierarchical_bootstrap_seed": BOOTSTRAP_SEED,
                "resamples": formal.BOOTSTRAP_RESAMPLES,
                "classical_materiality_percent": -2.0,
                "beta_zero_strict_improvement_percent": 0.0,
                "two_sided_95_upper_below_zero": True,
                "paired_seed_minimum": 3,
                "lower_is_better": True,
                "primary_endpoints": list(PRIMARY_ENDPOINTS),
            },
            "guards": {
                "tail_sync_no_harm_percent": 5.0,
                "fast_common_mean_and_cvar_no_harm_percent": 5.0,
                "slow_common_mean_and_cvar_no_harm_percent": 2.0,
                "storage_relative_no_harm_percent": 5.0,
                "command_and_actual_abs_system_pu_max": 0.36,
                "soc_range": [0.20, 0.80],
                "zero_constraint_violations": True,
                "zero_saturation_reasons": True,
                "mechanism_engagement_required": True,
                "controller_failure_is_outcome_not_integrity": True,
            },
            "sources": sources,
            "formal_trace_count_at_freeze": 0,
        }
        digest = formal._write_new(manifest_path, payload)
        print(f"[sealed] {manifest_path} sha256={digest}", flush=True)


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


def analyse_formal(
    manifest_path: Path,
    expected: str,
    out_dir: Path,
) -> None:
    """Apply the frozen R342 analysis exactly once to the complete matrix."""

    from probes.r342_limited_reverse_decision import classify_r342

    with _configured_formal() as formal:
        manifest = formal._verify(manifest_path, expected)
        bank, _ = formal.load_scenario_bank(
            formal.FORMAL_BANK,
            expected_sha256=manifest["formal_bank"]["sha256"],
        )
        bank_names = [row["name"] for row in bank["scenarios"]]
        q0_records = formal._q0_records(manifest)
        records: dict[str, list[dict[str, Any]]] = {
            arm: [] for arm in formal.ARMS
        }
        records["q0"] = [q0_records[name] for name in bank_names]
        trace_hashes = dict(manifest["screen"]["frozen_q0_trace_hashes"])
        failures: list[dict[str, Any]] = []
        for scenario in bank["scenarios"]:
            for arm in formal.NEW_TRACE_ARMS:
                path = formal._trace_path(out_dir, scenario["name"], arm)
                record = formal._validate_new_trace(
                    path,
                    scenario,
                    arm,
                    manifest,
                    expected,
                )
                digest = formal.sha256_file(path)
                trace_hashes[str(path.relative_to(ROOT)).replace("\\", "/")] = digest
                records[arm].append(record)
                if not record.get("completed") or record.get("tds_failed"):
                    failures.append(
                        {
                            "scenario": scenario["name"],
                            "arm": arm,
                            "completed": bool(record.get("completed")),
                            "tds_failed": bool(record.get("tds_failed")),
                            "setup_error": record.get("setup_error"),
                            "trace_sha256": digest,
                        }
                    )
        if failures:
            summary = {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "phase": formal.PHASE,
                "formal_seal_sha256": expected,
                "formal_bank_sha256": manifest["formal_bank"]["sha256"],
                "decision": {
                    "classification": "CONTROLLER-OUTCOME-FAILURE",
                    "reason": "one or more retained controller outcomes failed",
                    "integrity_valid": True,
                },
                "completion": {
                    "expected_matrix": 288,
                    "reused_q0": 24,
                    "new_records_observed": sum(
                        len(rows) for arm, rows in records.items() if arm != "q0"
                    ),
                    "controller_outcome_failures": failures,
                },
                "trace_hashes": dict(sorted(trace_hashes.items())),
            }
            summary_digest = formal._write_new(
                out_dir / "formal_summary.json", summary
            )
            formal._write_new(
                out_dir / "provenance.json",
                {
                    "schema_version": 1,
                    "round": ROUND_ID,
                    "formal_seal_sha256": expected,
                    "summary_sha256": summary_digest,
                    "trace_hashes": dict(sorted(trace_hashes.items())),
                    "paper_files_modified": False,
                },
            )
            return

        grid: dict[str, dict[str, dict[str, Any]]] = {
            name: {} for name in bank_names
        }
        action_audits: dict[str, dict[str, Any]] = {
            arm: {} for arm in formal.ARMS
        }
        for arm in formal.ARMS:
            for record in records[arm]:
                row = formal._endpoint_row(record)
                grid[record["scenario"]][arm] = row
                action_audits[arm][record["scenario"]] = formal.audit_vector_action(
                    row
                )
        arm_summaries = {
            arm: formal._summary(
                [grid[name][arm] for name in bank_names],
                records[arm],
            )
            for arm in formal.ARMS
        }
        grouped_summaries = {
            family: formal._summary(
                [
                    grid[name][f"{family}_s{seed}"]
                    for seed in SEEDS
                    for name in bank_names
                ],
                [
                    record
                    for seed in SEEDS
                    for record in records[f"{family}_s{seed}"]
                ],
            )
            for family in ("beta0", "beta0p1")
        }
        contrasts = {
            "classical_vs_q0": formal._classical_contrast(grid, bank_names),
            "beta0_vs_classical": formal._hierarchical(
                grid, bank_names, "beta0", "classical_edge"
            ),
            "beta0p1_vs_classical": formal._hierarchical(
                grid, bank_names, "beta0p1", "classical_edge"
            ),
            "beta0p1_vs_beta0": formal._hierarchical(
                grid, bank_names, "beta0p1", "beta0"
            ),
        }
        classical_seed_count, beta0_seed_count, seed_rows = _seed_directionality(
            grid,
            bank_names,
        )
        absolute_storage = {
            arm: {
                **arm_summaries[arm]["storage"],
                "pass": formal._absolute_storage_pass(
                    arm_summaries[arm]["storage"]
                ),
            }
            for arm in formal.ARMS
        }
        action_pass = {
            family: all(
                all(audit.values())
                for seed in SEEDS
                for audit in action_audits[f"{family}_s{seed}"].values()
            )
            for family in ("beta0", "beta0p1")
        }
        relative_guards = {
            family: formal._relative_guards(
                grouped_summaries[family],
                arm_summaries["classical_edge"],
            )
            for family in ("beta0", "beta0p1")
        }
        candidate_guards = {
            "action_contract": action_pass["beta0p1"],
            "absolute_storage": all(
                absolute_storage[f"beta0p1_s{seed}"]["pass"] for seed in SEEDS
            ),
            "relative_no_harm": relative_guards["beta0p1"]["pass"],
            "controller_outcome_complete": True,
        }
        integrity = {
            "complete_288_matrix": all(
                set(grid[name]) == set(formal.ARMS) for name in bank_names
            ),
            "formal_bank_screen_pass": True,
            "all_action_execution_audits": all(
                all(audit.values())
                for arm in formal.ARMS
                for audit in action_audits[arm].values()
            ),
            "training_budget_and_seed_set_verified": True,
            "bootstrap_contract_complete": True,
            "provenance_hashes_verified": True,
        }
        try:
            engagement = _mechanism_engagement(records)
            engagement["telemetry_valid"] = True
        except ValueError as error:
            engagement = {
                "engaged": False,
                "telemetry_valid": False,
                "error": str(error),
            }
            integrity["mechanism_telemetry_valid"] = False
        decision = classify_r342(
            integrity_valid=all(integrity.values()),
            mechanism_engaged=bool(engagement["engaged"]),
            controller_outcomes_complete=True,
            candidate_vs_classical=contrasts["beta0p1_vs_classical"],
            candidate_vs_beta0=contrasts["beta0p1_vs_beta0"],
            candidate_vs_classical_seed_count=classical_seed_count,
            candidate_vs_beta0_seed_count=beta0_seed_count,
            positive_claim_guards=candidate_guards,
        )
        decision["integrity_guards"] = integrity
        summary = {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "phase": formal.PHASE,
            "formal_seal_sha256": expected,
            "formal_bank_sha256": manifest["formal_bank"]["sha256"],
            "decision": decision,
            "completion": {
                "expected_matrix": 288,
                "reused_q0": 24,
                "new_records_observed": 264,
                "controller_outcome_failures": [],
            },
            "mechanism_engagement": engagement,
            "arm_summaries": arm_summaries,
            "grouped_summaries": grouped_summaries,
            "contrasts": contrasts,
            "seed_directionality": seed_rows,
            "relative_guards_vs_classical": relative_guards,
            "positive_claim_guards": {"beta0p1": candidate_guards},
            "absolute_storage_guards": absolute_storage,
            "action_audits": action_audits,
            "trace_hashes": dict(sorted(trace_hashes.items())),
        }
        summary_digest = formal._write_new(out_dir / "formal_summary.json", summary)
        provenance_digest = formal._write_new(
            out_dir / "provenance.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "repository_head": formal._git_head(),
                "formal_seal_sha256": expected,
                "summary_sha256": summary_digest,
                "trace_hashes": dict(sorted(trace_hashes.items())),
                "paper_files_modified": False,
            },
        )
        print(
            f"[analysed] classification={decision['classification']} "
            f"summary_sha256={summary_digest} provenance_sha256={provenance_digest}",
            flush=True,
        )


def _wait_for_canary_barrier(timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    while len(list(CANARY_BARRIER_DIR.glob("ready_*.marker"))) < FORMAL_SHARD_COUNT:
        if time.monotonic() >= deadline:
            raise TimeoutError("sixteen R342 canary workers did not reach the barrier")
        time.sleep(0.05)


def run_physical_canary_worker(
    manifest_path: Path,
    expected: str,
    *,
    shard_index: int,
    shard_count: int,
    barrier_timeout_seconds: float = 60.0,
) -> None:
    """Run one fixed 15-step cell solely to validate sixteen-way execution."""

    if shard_count != FORMAL_SHARD_COUNT or not 0 <= shard_index < shard_count:
        raise ValueError("R342 physical canary requires exactly sixteen workers")
    contract = build_physical_canary_contract()
    task = contract["tasks"][shard_index]
    path = CANARY_TRACE_DIR / f"canary_{shard_index}.json"
    if path.exists():
        raise FileExistsError(f"physical canary is create-only: {path}")
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
        observed_workers = _r342_python_process_count()
        if observed_workers != FORMAL_SHARD_COUNT:
            raise RuntimeError(
                f"physical canary observed {observed_workers} workers, expected 16"
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
                phase="r342-sixteen-worker-physical-canary",
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
                "question": QUESTION_ID,
                "experiment": "r342_physical_concurrency_canary",
                "phase": "r342-sixteen-worker-physical-canary",
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
            raise RuntimeError(f"physical canary worker failed: {shard_index}")


def verify_physical_canary(
    manifest_path: Path,
    expected: str,
) -> str:
    """Accept the canary only from sixteen valid overlapping worker records."""

    with _configured_formal() as formal:
        manifest = formal._verify(manifest_path, expected)
        starts: list[int] = []
        finishes: list[int] = []
        scratch_dirs: set[str] = set()
        record_hashes: dict[str, str] = {}
        for task in build_physical_canary_contract()["tasks"]:
            index = task["shard_index"]
            path = CANARY_TRACE_DIR / f"canary_{index}.json"
            record = formal._load_json(path)
            expected_fields = {
                "round": ROUND_ID,
                "phase": "r342-sixteen-worker-physical-canary",
                "controller": task["arm"],
                "formal_seal_sha256": expected,
                "formal_bank_sha256": manifest["formal_bank"]["sha256"],
                "execution_shard_index": index,
                "execution_shard_count": FORMAL_SHARD_COUNT,
                "observed_concurrent_workers": FORMAL_SHARD_COUNT,
                "performance_use": "forbidden",
            }
            for key, value in expected_fields.items():
                if record.get(key) != value:
                    raise ValueError(f"physical canary provenance mismatch: {key}")
            if not record.get("completed") or record.get("tds_failed"):
                raise ValueError(f"physical canary did not complete: {index}")
            starts.append(int(record["simulation_started_ns"]))
            finishes.append(int(record["simulation_finished_ns"]))
            scratch_dirs.add(str(record["scratch_working_directory"]))
            record_hashes[str(path.relative_to(ROOT)).replace("\\", "/")] = (
                formal.sha256_file(path)
            )
        log_names = sorted(path.name for path in CANARY_LOG_DIR.glob("shard_*.log"))
        expected_logs = [f"shard_{index}.log" for index in range(FORMAL_SHARD_COUNT)]
        if log_names != expected_logs:
            raise ValueError(f"physical canary log set mismatch: {log_names}")
        if len(scratch_dirs) != FORMAL_SHARD_COUNT:
            raise ValueError("physical canary scratch directories collided")
        if max(starts) >= min(finishes):
            raise ValueError("sixteen physical canary simulations did not overlap")
        return formal._write_new(
            CANARY_GATE,
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "classification": "PASS",
                "formal_seal_sha256": expected,
                "formal_bank_sha256": manifest["formal_bank"]["sha256"],
                "worker_count": FORMAL_SHARD_COUNT,
                "unique_scratch_directory_count": len(scratch_dirs),
                "all_workers_overlapped": True,
                "record_hashes": dict(sorted(record_hashes.items())),
                "performance_use": "forbidden",
                "automatic_formal_release": False,
            },
        )


def _require_canary_pass(expected_formal_seal: str) -> None:
    gate = _load_hashed_json(CANARY_GATE)
    if gate.get("round") != ROUND_ID or gate.get("classification") != "PASS":
        raise ValueError("R342 full formal execution requires a passing canary")
    if gate.get("formal_seal_sha256") != expected_formal_seal:
        raise ValueError("R342 canary belongs to a different formal seal")
    if gate.get("worker_count") != FORMAL_SHARD_COUNT:
        raise ValueError("R342 canary worker count drift")
    if gate.get("automatic_formal_release") is not False:
        raise ValueError("R342 canary release contract drift")


def _artifact_digest(path: Path) -> str:
    sidecar = path.with_name(path.name + ".sha256")
    expected = sidecar.read_text(encoding="utf-8").split()[0].lower()
    actual = _sha256_file(path)
    if actual != expected:
        raise ValueError(f"artifact sidecar mismatch: {path}")
    return actual


def verify_training_matrix(
    manifest_path: Path = TRAINING_SEAL,
    out_root: Path = TRAINING_OUT,
) -> None:
    expected = _artifact_digest(manifest_path)
    with _configured_training() as training:
        training.verify_matrix(manifest_path, expected, out_root)


def _run_wsl_stage(*stage_args: str) -> None:
    if os.name != "nt":
        raise RuntimeError("R342 host orchestration must run from Windows")
    from scripts import run_parallel_wsl_shards as launcher

    command = [
        "wsl.exe",
        "--cd",
        launcher._wsl_path(ROOT),
        launcher.WSL_PYTHON,
        launcher.SCRATCH_LAUNCHER,
        "scripts/run_r342_limited_reverse_residual.py",
        *stage_args,
    ]
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"R342 WSL stage failed ({completed.returncode}): {' '.join(stage_args)}"
        )


def _run_host_shards(
    *,
    command: str,
    worker_count: int,
    global_task_count: int,
    log_dir: Path,
    worker_args: list[str],
    trace_dir: Path | None = None,
) -> None:
    launcher = ROOT / "scripts/run_parallel_wsl_shards.py"
    argv = [
        sys.executable,
        str(launcher),
        "--worker-script",
        "scripts/run_r342_limited_reverse_residual.py",
        "--shard-count",
        str(worker_count),
        "--process-budget",
        "16",
        "--global-task-count",
        str(global_task_count),
        "--log-dir",
        str(log_dir),
    ]
    if trace_dir is not None:
        argv.extend(["--trace-dir", str(trace_dir)])
    argv.extend(["--", command, *worker_args])
    completed = subprocess.run(argv, cwd=ROOT, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"R342 parallel stage failed ({completed.returncode}): {command}"
        )


def _record_attempt_failure(
    phase: str,
    error: BaseException,
    attempt_digest: str,
) -> None:
    if FORMAL_FAILURE.exists():
        return
    _write_new_json(
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


def _require_smoke_release() -> tuple[str, str, dict[str, Any]]:
    if FORMAL_FAILURE.exists():
        raise RuntimeError("R342 attempt has a recorded failure; retry is forbidden")
    attempt_digest = _artifact_digest(FORMAL_ATTEMPT)
    training_digest = _artifact_digest(TRAINING_SEAL)
    gate_digest = _artifact_digest(TRAINING_OUT / "smoke_gate.json")
    ready = _load_hashed_json(SMOKE_READY_RECORD)
    expected = {
        "round": ROUND_ID,
        "phase": "training-smoke-ready",
        "attempt_sha256": attempt_digest,
        "training_seal_sha256": training_digest,
        "smoke_gate_sha256": gate_digest,
        "automatic_full_training_release": False,
    }
    for key, value in expected.items():
        if ready.get(key) != value:
            raise ValueError(f"R342 smoke release mismatch: {key}")
    gate = _load_hashed_json(TRAINING_OUT / "smoke_gate.json")
    if gate.get("classification") != "PASS" or gate.get("worker_count") != 5:
        raise ValueError("R342 full training requires a passing five-worker smoke")
    return attempt_digest, training_digest, gate


def execute_through_smoke() -> str:
    """Start the only attempt, measure five workers, then stop for review."""

    if os.name != "nt":
        raise RuntimeError("execute must be launched from the Windows host")
    _run_wsl_stage("verify-rehearsal")
    attempt_digest = _write_new_json(
        FORMAL_ATTEMPT,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "phase": "staged-attempt",
            "attempt_number": 1,
            "execution_stage_plan": build_execution_stage_plan(),
            "automatic_retry": False,
            "automatic_full_training_release": False,
            "automatic_formal_release": False,
        },
    )
    try:
        from scripts import run_parallel_wsl_shards as launcher

        _run_wsl_stage("prepare-training")
        training_digest = _artifact_digest(TRAINING_SEAL)
        smoke_barrier = launcher._wsl_path(TRAINING_OUT / "smoke_barrier")
        _run_host_shards(
            command="training-worker",
            worker_count=5,
            global_task_count=5,
            log_dir=TRAINING_LOG_DIR / "smoke",
            worker_args=[
                "--expected-manifest-sha256",
                training_digest,
                "--smoke-episodes",
                "1",
                "--barrier-dir",
                smoke_barrier,
            ],
        )
        _run_wsl_stage("verify-training-smoke")
        gate_path = TRAINING_OUT / "smoke_gate.json"
        gate = _load_hashed_json(gate_path)
        return _write_new_json(
            SMOKE_READY_RECORD,
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "phase": "training-smoke-ready",
                "attempt_sha256": attempt_digest,
                "training_seal_sha256": training_digest,
                "smoke_gate_sha256": _artifact_digest(gate_path),
                "timing": gate["timing"],
                "automatic_full_training_release": False,
            },
        )
    except BaseException as error:
        _record_attempt_failure("training-smoke-failure", error, attempt_digest)
        raise


def continue_through_canary() -> str:
    """After manual smoke review, run training and stop at the canary gate."""

    if os.name != "nt":
        raise RuntimeError("continuation must be launched from the Windows host")
    attempt_digest, training_digest, _ = _require_smoke_release()
    try:
        from scripts import run_parallel_wsl_shards as launcher

        full_barrier = launcher._wsl_path(TRAINING_OUT / "training_barrier")
        _run_host_shards(
            command="training-worker",
            worker_count=5,
            global_task_count=5,
            log_dir=TRAINING_LOG_DIR / "full",
            worker_args=[
                "--expected-manifest-sha256",
                training_digest,
                "--barrier-dir",
                full_barrier,
            ],
        )
        _run_wsl_stage("verify-training")

        _run_wsl_stage("prepare-fresh")
        fresh_digest = _artifact_digest(FRESH_SEAL)
        _run_host_shards(
            command="fresh-worker",
            worker_count=FRESH_SHARD_COUNT,
            global_task_count=24,
            log_dir=FRESH_LOG_DIR,
            trace_dir=FRESH_OUT / "screen_traces",
            worker_args=["--expected-manifest-sha256", fresh_digest],
        )
        _run_wsl_stage("analyse-fresh", "--expected-manifest-sha256", fresh_digest)

        _run_wsl_stage("prepare-formal")
        formal_digest = _artifact_digest(FORMAL_SEAL)
        _run_host_shards(
            command="canary-worker",
            worker_count=FORMAL_SHARD_COUNT,
            global_task_count=FORMAL_SHARD_COUNT,
            log_dir=CANARY_LOG_DIR,
            trace_dir=CANARY_TRACE_DIR,
            worker_args=["--expected-manifest-sha256", formal_digest],
        )
        _run_wsl_stage("verify-canary", "--expected-manifest-sha256", formal_digest)
        return _write_new_json(
            CANARY_READY_RECORD,
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "phase": "physical-canary-ready",
                "attempt_sha256": attempt_digest,
                "training_summary_sha256": _artifact_digest(
                    TRAINING_OUT / "training_matrix_summary.json"
                ),
                "fresh_screen_summary_sha256": _artifact_digest(
                    FRESH_OUT / "screen_summary.json"
                ),
                "formal_seal_sha256": formal_digest,
                "canary_gate_sha256": _artifact_digest(CANARY_GATE),
                "automatic_formal_release": False,
            },
        )
    except BaseException as error:
        _record_attempt_failure("training-through-canary-failure", error, attempt_digest)
        raise


def execute_full_formal() -> str:
    """Explicitly release the sealed 264-trajectory matrix after canary PASS."""

    if os.name != "nt":
        raise RuntimeError("formal execution must be launched from the Windows host")
    formal_digest = _artifact_digest(FORMAL_SEAL)
    _require_canary_pass(formal_digest)
    try:
        _run_host_shards(
            command="formal-worker",
            worker_count=FORMAL_SHARD_COUNT,
            global_task_count=264,
            log_dir=FORMAL_LOG_DIR,
            trace_dir=FORMAL_OUT / "traces",
            worker_args=["--expected-manifest-sha256", formal_digest],
        )
        _run_wsl_stage("analyse-formal", "--expected-manifest-sha256", formal_digest)
        return _write_new_json(
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
        if not FORMAL_FAILURE.exists():
            _write_new_json(
                FORMAL_FAILURE,
                {
                    "schema_version": 1,
                    "round": ROUND_ID,
                    "phase": "formal-execution-failure",
                    "error_type": type(error).__name__,
                    "error": str(error),
                    "traceback": traceback.format_exc(),
                    "automatic_retry": False,
                },
            )
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("contract")
    subparsers.add_parser("prepare-training")
    subparsers.add_parser("rehearse")
    subparsers.add_parser("verify-rehearsal")
    worker = subparsers.add_parser("training-worker")
    worker.add_argument("--manifest", type=Path, default=TRAINING_SEAL)
    worker.add_argument("--expected-manifest-sha256", required=True)
    worker.add_argument("--out-root", type=Path, default=TRAINING_OUT)
    worker.add_argument("--smoke-episodes", type=int)
    worker.add_argument("--barrier-dir", type=Path)
    worker.add_argument("--barrier-timeout-seconds", type=float, default=60.0)
    worker.add_argument("--shard-index", type=int, required=True)
    worker.add_argument("--shard-count", type=int, required=True)
    smoke_gate = subparsers.add_parser("verify-training-smoke")
    smoke_gate.add_argument("--out-root", type=Path, default=TRAINING_OUT)
    verify_training = subparsers.add_parser("verify-training")
    verify_training.add_argument("--manifest", type=Path, default=TRAINING_SEAL)
    verify_training.add_argument("--out-root", type=Path, default=TRAINING_OUT)
    subparsers.add_parser("prepare-fresh")
    fresh_worker = subparsers.add_parser("fresh-worker")
    fresh_worker.add_argument("--manifest", type=Path, default=FRESH_SEAL)
    fresh_worker.add_argument("--expected-manifest-sha256", required=True)
    fresh_worker.add_argument("--out-dir", type=Path, default=FRESH_OUT)
    fresh_worker.add_argument("--shard-index", type=int, required=True)
    fresh_worker.add_argument("--shard-count", type=int, required=True)
    fresh_analyse = subparsers.add_parser("analyse-fresh")
    fresh_analyse.add_argument("--manifest", type=Path, default=FRESH_SEAL)
    fresh_analyse.add_argument("--expected-manifest-sha256", required=True)
    fresh_analyse.add_argument("--out-dir", type=Path, default=FRESH_OUT)
    prepare_formal = subparsers.add_parser("prepare-formal")
    prepare_formal.add_argument("--manifest", type=Path, default=FORMAL_SEAL)
    prepare_formal.add_argument("--out-dir", type=Path, default=FORMAL_OUT)
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
    canary_worker = subparsers.add_parser("canary-worker")
    canary_worker.add_argument("--manifest", type=Path, default=FORMAL_SEAL)
    canary_worker.add_argument("--expected-manifest-sha256", required=True)
    canary_worker.add_argument("--barrier-timeout-seconds", type=float, default=60.0)
    canary_worker.add_argument("--shard-index", type=int, required=True)
    canary_worker.add_argument("--shard-count", type=int, required=True)
    canary_verify = subparsers.add_parser("verify-canary")
    canary_verify.add_argument("--manifest", type=Path, default=FORMAL_SEAL)
    canary_verify.add_argument("--expected-manifest-sha256", required=True)
    subparsers.add_parser("execute")
    subparsers.add_parser("continue-through-canary")
    subparsers.add_parser("execute-formal")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "contract":
        print(json.dumps(build_contract(), sort_keys=True))
    elif args.command == "prepare-training":
        prepare_training_seal()
    elif args.command == "rehearse":
        digest = rehearse()
        print(f"[rehearsed] sha256={digest}", flush=True)
    elif args.command == "verify-rehearsal":
        verify_rehearsal()
        print("[rehearsal-verified]", flush=True)
    elif args.command == "training-worker":
        return run_training_worker(
            args.manifest,
            args.expected_manifest_sha256,
            args.out_root,
            shard_index=args.shard_index,
            shard_count=args.shard_count,
            smoke_episodes=args.smoke_episodes,
            barrier_dir=args.barrier_dir,
            barrier_timeout_seconds=args.barrier_timeout_seconds,
        )
    elif args.command == "verify-training-smoke":
        digest = verify_training_smoke(args.out_root)
        print(f"[training-smoke-pass] sha256={digest}", flush=True)
    elif args.command == "verify-training":
        verify_training_matrix(args.manifest, args.out_root)
        print("[training-matrix-verified]", flush=True)
    elif args.command == "prepare-fresh":
        prepare_fresh_bank_seal()
    elif args.command == "fresh-worker":
        run_fresh_bank_shard(
            args.manifest,
            args.expected_manifest_sha256,
            args.out_dir,
            shard_index=args.shard_index,
            shard_count=args.shard_count,
        )
    elif args.command == "analyse-fresh":
        analyse_fresh_bank(
            args.manifest,
            args.expected_manifest_sha256,
            args.out_dir,
        )
    elif args.command == "prepare-formal":
        prepare_formal_seal(args.manifest, args.out_dir)
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
    elif args.command == "canary-worker":
        run_physical_canary_worker(
            args.manifest,
            args.expected_manifest_sha256,
            shard_index=args.shard_index,
            shard_count=args.shard_count,
            barrier_timeout_seconds=args.barrier_timeout_seconds,
        )
    elif args.command == "verify-canary":
        digest = verify_physical_canary(
            args.manifest,
            args.expected_manifest_sha256,
        )
        print(f"[physical-canary-pass] sha256={digest}", flush=True)
    elif args.command == "execute":
        digest = execute_through_smoke()
        print(f"[training-smoke-ready] sha256={digest}", flush=True)
    elif args.command == "continue-through-canary":
        digest = continue_through_canary()
        print(f"[physical-canary-ready] sha256={digest}", flush=True)
    else:
        digest = execute_full_formal()
        print(f"[formal-execution-complete] sha256={digest}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
