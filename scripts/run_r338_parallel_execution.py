#!/usr/bin/env python3
"""R338 execution-only successor for the frozen ICEMS comparison.

This adapter deliberately reuses the prospectively sealed R337 checkpoints
and controller-blind fresh bank while excluding every R337 formal trajectory.
It changes round identity, output paths, and scheduling only.  The Windows
host launches three independent WSL workers with
``scripts/run_parallel_wsl_shards.py``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any


_THREAD_ENVIRONMENT = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
)
for _thread_variable in _THREAD_ENVIRONMENT:
    os.environ[_thread_variable] = "1"


ROUND_ID = "R338"
UPSTREAM_ROUND_ID = "R337"
QUESTION_ID = "Q-0088"
TITLE = (
    "Decoupling-Oriented Coordination of Paralleled VSGs With "
    "Multi-Agent Reinforcement Learning"
)
SEEDS = (421, 463, 509, 557, 601)
ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))
R337_TRAINING_OUT = ROOT / "results/r337_prior_residual_training"
R337_FRESH_OUT = ROOT / "results/r337_fresh_bank"
R293_CLASSICAL_GUARD = (
    ROOT / "results/r293_classical_guard/classical_guard_summary.json"
)
FORMAL_SEAL = ROOT / "memory/rounds/R338/formal_seal.json"
FORMAL_OUT = ROOT / "results/r338_formal_evaluation"
CANARY_OUT = ROOT / "results/r338_parallel_canary"
CANARY_RECORD_DIR = CANARY_OUT / "traces"
CANARY_BARRIER_DIR = CANARY_OUT / "barrier"
CANARY_LOG_DIR = CANARY_OUT / "logs"
CANARY_GATE = CANARY_OUT / "canary_gate.json"
FORMAL_LOG_DIR = ROOT / "results/r338_parallel_logs"
CANARY_STEPS = 15
CANARY_ARMS = (
    "classical_edge",
    "central_prior_s421",
    "distributed_prior_s421",
)
SHARD_COUNT = 3
NEW_FORMAL_TRAJECTORIES = 264


def build_contract() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "title": TITLE,
        "title_changed": False,
        "scientific_object_changed": False,
        "upstreams": {
            "training": "results/r337_prior_residual_training",
            "fresh_bank": "results/r337_fresh_bank",
            "checkpoint_metadata_round": UPSTREAM_ROUND_ID,
        },
        "forbidden_inputs": [
            "results/r337_formal_evaluation",
            "memory/rounds/R337/formal_seal.json",
            "memory/rounds/R337/formal_attempt.json",
            "memory/rounds/R337/formal_failure.json",
        ],
        "execution": {
            "wsl_workers": SHARD_COUNT,
            "native_threads_per_worker": 1,
            "new_formal_trajectories": NEW_FORMAL_TRAJECTORIES,
            "reused_q0_trajectories": 24,
            "automatic_retry": False,
        },
    }


def build_canary_contract() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "worker_count": SHARD_COUNT,
        "steps": CANARY_STEPS,
        "arms": list(CANARY_ARMS),
        "scenario_selection": "first_frozen_scenario",
        "performance_endpoints_inspected": False,
        "automatic_formal_release": False,
    }


def _checkpoint_path(architecture: str, seed: int) -> Path:
    return R337_TRAINING_OUT / f"{architecture}_s{seed}" / "final.pt"


def _controller_contract_path(architecture: str, seed: int) -> Path:
    return R337_TRAINING_OUT / f"{architecture}_s{seed}" / "controller_contract.json"


def _formal_source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R338/plan.md",
        "question": ROOT / "memory/questions/Q-0088.md",
        "r338_adapter": Path(__file__).resolve(),
        "r338_tests": ROOT / "tests/test_r338_parallel_execution.py",
        "parallel_launcher": ROOT / "scripts/run_parallel_wsl_shards.py",
        "parallel_launcher_tests": ROOT / "tests/test_parallel_wsl_shards.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "scratch_launcher_tests": ROOT / "tests/test_andes_scratch_launcher.py",
        "inherited_formal_core": ROOT / "scripts/run_r293_formal.py",
        "decision_probe": ROOT / "probes/r293_comparison.py",
        "vector_runner": ROOT / "src/andes_rl_kundur/evaluation/vector_residual.py",
        "sealed_bank": ROOT / "src/andes_rl_kundur/evaluation/sealed_bank.py",
        "prior_actor": ROOT / "src/andes_rl_kundur/agents/classical_prior_td3.py",
        "vector_actor": ROOT / "src/andes_rl_kundur/agents/vector_residual_td3.py",
        "classical_controller": (
            ROOT / "src/andes_rl_kundur/control/classical_edge_residual.py"
        ),
        "vector_environment": (
            ROOT / "src/andes_rl_kundur/env/andes/distributed_residual_env.py"
        ),
        "prior_environment": (
            ROOT / "src/andes_rl_kundur/env/andes/prior_residual_env.py"
        ),
        "vector_contract": (
            ROOT / "src/andes_rl_kundur/control/vector_inertia_residual.py"
        ),
        "r337_training_seal": ROOT / "memory/rounds/R337/training_seal.json",
        "r337_fresh_bank_seal": (
            ROOT / "memory/rounds/R337/fresh_bank_screen_seal.json"
        ),
        "formal_bank": R337_FRESH_OUT / "formal_bank.json",
        "screen_summary": R337_FRESH_OUT / "screen_summary.json",
        "screen_contract": R337_FRESH_OUT / "feasibility_screen_contract.json",
        "screen_provenance": R337_FRESH_OUT / "provenance.json",
        "training_summary": R337_TRAINING_OUT / "training_matrix_summary.json",
        "classical_guard": R293_CLASSICAL_GUARD,
    }


@contextmanager
def _configured_formal():
    """Temporarily route the frozen evaluator to R338 create-only outputs."""

    from scripts import run_r293_formal as base

    original_make_controller = base._make_controller

    def load_r337_checkpoint(
        arm: str, config: dict[str, Any]
    ) -> tuple[Any, dict[str, Any]]:
        # Checkpoints truthfully retain their prospective R337 metadata.  Only
        # the new physical trace and seal carry R338 identity.
        current_round = base.ROUND_ID
        base.ROUND_ID = UPSTREAM_ROUND_ID
        try:
            return original_make_controller(arm, config)
        finally:
            base.ROUND_ID = current_round

    arms = (
        "q0",
        "classical_edge",
        *(f"central_prior_s{seed}" for seed in SEEDS),
        *(f"distributed_prior_s{seed}" for seed in SEEDS),
    )
    replacements = {
        "ROUND_ID": ROUND_ID,
        "QUESTION_ID": QUESTION_ID,
        "SEEDS": SEEDS,
        "BOOTSTRAP_SEED": 2026080402,
        "ARMS": arms,
        "NEW_TRACE_ARMS": arms[1:],
        "FRESH_DIR": R337_FRESH_OUT,
        "FORMAL_BANK": R337_FRESH_OUT / "formal_bank.json",
        "SCREEN_SUMMARY": R337_FRESH_OUT / "screen_summary.json",
        "SCREEN_CONTRACT": R337_FRESH_OUT / "feasibility_screen_contract.json",
        "SCREEN_PROVENANCE": R337_FRESH_OUT / "provenance.json",
        "TRAINING_SUMMARY": R337_TRAINING_OUT / "training_matrix_summary.json",
        "CLASSICAL_GUARD": R293_CLASSICAL_GUARD,
        "DEFAULT_SEAL": FORMAL_SEAL,
        "DEFAULT_OUT": FORMAL_OUT,
        "_checkpoint_path": _checkpoint_path,
        "_contract_path": _controller_contract_path,
        "_source_paths": _formal_source_paths,
        "_make_controller": load_r337_checkpoint,
    }
    previous = {name: getattr(base, name) for name in replacements}
    for name, value in replacements.items():
        setattr(base, name, value)
    try:
        yield base
    finally:
        for name, value in previous.items():
            setattr(base, name, value)


def _artifact_digest(path: Path) -> str:
    sidecar = path.with_name(path.name + ".sha256")
    expected = sidecar.read_text(encoding="utf-8").split()[0].lower()
    from andes_rl_kundur.evaluation.sealed_bank import sha256_file

    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(f"artifact sidecar mismatch: {path}")
    return actual


def _load_hashed_json(path: Path) -> dict[str, Any]:
    _artifact_digest(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def prepare(
    manifest_path: Path = FORMAL_SEAL,
    out_dir: Path = FORMAL_OUT,
    *,
    canary_out: Path = CANARY_OUT,
) -> None:
    if out_dir.exists():
        raise FileExistsError(f"new R338 formal output must be absent: {out_dir}")
    if canary_out.exists():
        raise FileExistsError(f"R338 canary output must be absent at seal: {canary_out}")
    with _configured_formal() as formal:
        formal.prepare(manifest_path, out_dir)


def _r338_worker_count(command: str) -> int:
    if os.name == "nt":
        return 0
    count = 0
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cmdline = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(
                "utf-8", errors="replace"
            )
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if "run_r338_parallel_execution.py" in cmdline and command in cmdline:
            count += 1
    return count


def _wait_for_barrier(barrier_dir: Path, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    while len(list(barrier_dir.glob("ready_*.marker"))) < SHARD_COUNT:
        if time.monotonic() >= deadline:
            raise TimeoutError("three R338 canary workers did not reach the barrier")
        time.sleep(0.05)


def run_canary_worker(
    manifest_path: Path,
    expected: str,
    out_dir: Path,
    barrier_dir: Path,
    shard_index: int,
    shard_count: int,
    barrier_timeout_seconds: float,
) -> None:
    if shard_count != SHARD_COUNT or not 0 <= shard_index < SHARD_COUNT:
        raise ValueError("R338 canary requires exactly three fixed workers")
    path = out_dir / f"canary_{shard_index}.json"
    if path.exists():
        raise FileExistsError(f"refusing to reuse canary record: {path}")

    with _configured_formal() as formal:
        manifest = formal._verify(manifest_path, expected)
        bank, _ = formal.load_scenario_bank(
            formal.FORMAL_BANK,
            expected_sha256=manifest["formal_bank"]["sha256"],
        )
        scenario = bank["scenarios"][0]
        arm = CANARY_ARMS[shard_index]
        controller, controller_config = formal._make_controller(
            arm, manifest["arms"][arm]
        )

        barrier_dir.mkdir(parents=True, exist_ok=True)
        ready = barrier_dir / f"ready_{shard_index}.marker"
        with ready.open("x", encoding="utf-8", errors="strict") as handle:
            handle.write(f"{time.time_ns()}\n")
        _wait_for_barrier(barrier_dir, barrier_timeout_seconds)
        observed_workers = _r338_worker_count("canary-worker")
        if observed_workers != SHARD_COUNT:
            raise RuntimeError(
                f"physical canary observed {observed_workers} workers, expected 3"
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
                steps=CANARY_STEPS,
                phase="r338-three-worker-physical-canary",
                evidence_hashes={
                    "formal_seal": expected,
                    "formal_bank": manifest["formal_bank"]["sha256"],
                },
            )
        except Exception as exc:
            record = {
                "schema_version": 1,
                "controller": arm,
                "scenario": scenario["name"],
                "delta_u": dict(scenario["delta_u"]),
                "requested_steps": CANARY_STEPS,
                "n_steps": 0,
                "tds_failed": True,
                "completed": False,
                "traces": [],
                "setup_error": {"type": type(exc).__name__, "message": str(exc)},
                "seed": formal.ENV_SEED,
            }
        finished_ns = time.time_ns()
        record.update(
            {
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "experiment": "r338_parallel_execution_canary",
                "phase": "r338-three-worker-physical-canary",
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
            f"[canary {shard_index + 1}/3] {path.name} "
            f"completed={record.get('completed')} sha256={digest}",
            flush=True,
        )
        if not record.get("completed") or record.get("tds_failed"):
            raise RuntimeError(f"physical canary worker {shard_index} did not complete")


def _formal_run_shard(
    formal: Any,
    manifest_path: Path,
    expected: str,
    out_dir: Path,
    shard_index: int,
    shard_count: int,
) -> None:
    manifest = formal._verify(manifest_path, expected)
    if shard_count != formal.SHARD_COUNT or not 0 <= shard_index < shard_count:
        raise ValueError("formal shard contract drift")
    bank, _ = formal.load_scenario_bank(
        formal.FORMAL_BANK, expected_sha256=manifest["formal_bank"]["sha256"]
    )
    tasks = [
        (scenario, arm)
        for scenario in bank["scenarios"]
        for arm in formal.NEW_TRACE_ARMS
    ]
    selected = [
        task for index, task in enumerate(tasks) if index % shard_count == shard_index
    ]
    controllers: dict[str, tuple[Any, dict[str, Any]]] = {}
    for index, (scenario, arm) in enumerate(selected, start=1):
        path = formal._trace_path(out_dir, scenario["name"], arm)
        if path.exists():
            raise FileExistsError(f"R338 formal execution is create-only: {path}")
        try:
            if arm not in controllers:
                controllers[arm] = formal._make_controller(arm, manifest["arms"][arm])
            controller, controller_config = controllers[arm]
            record = formal.run_vector_controller_scenario(
                controller,
                controller_name=arm,
                controller_config=controller_config,
                scenario_name=scenario["name"],
                delta_u=scenario["delta_u"],
                seed=formal.ENV_SEED,
                steps=formal.STEPS,
                phase="fresh-bank-twelve-arm-prior-residual-formal",
                evidence_hashes={
                    "formal_seal": expected,
                    "formal_bank": manifest["formal_bank"]["sha256"],
                },
            )
        except Exception as exc:
            record = {
                "schema_version": 1,
                "controller": arm,
                "scenario": scenario["name"],
                "delta_u": dict(scenario["delta_u"]),
                "requested_steps": formal.STEPS,
                "n_steps": 0,
                "tds_failed": True,
                "completed": False,
                "traces": [],
                "setup_error": {"type": type(exc).__name__, "message": str(exc)},
                "seed": formal.ENV_SEED,
            }
        record.update(
            {
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "experiment": "r338_parallel_execution_successor",
                "phase": "fresh-bank-twelve-arm-prior-residual-formal",
                "controller": arm,
                "location": scenario["location"],
                "sign": scenario["sign"],
                "severity": scenario["severity"],
                "formal_seal_sha256": expected,
                "formal_bank_sha256": manifest["formal_bank"]["sha256"],
                "execution_shard_index": shard_index,
                "execution_shard_count": shard_count,
            }
        )
        digest = formal._write_new(path, record)
        print(
            f"[formal {index:03d}/{len(selected):03d}] {path.name} "
            f"completed={record['completed']} sha256={digest}",
            flush=True,
        )


def verify_canary(
    manifest_path: Path,
    expected: str,
    canary_dir: Path = CANARY_OUT,
    log_dir: Path = CANARY_LOG_DIR,
) -> str:
    record_dir = canary_dir / "traces"
    barrier_dir = canary_dir / "barrier"
    gate_path = canary_dir / "canary_gate.json"
    with _configured_formal() as formal:
        manifest = formal._verify(manifest_path, expected)
        expected_names = [f"canary_{index}.json" for index in range(SHARD_COUNT)]
        observed_names = sorted(path.name for path in record_dir.glob("*.json"))
        if observed_names != expected_names:
            raise ValueError(
                f"canary record set mismatch: {observed_names} != {expected_names}"
            )
        ready_names = sorted(path.name for path in barrier_dir.glob("ready_*.marker"))
        if ready_names != [f"ready_{index}.marker" for index in range(SHARD_COUNT)]:
            raise ValueError(f"canary readiness set mismatch: {ready_names}")
        log_names = sorted(path.name for path in log_dir.glob("shard_*.log"))
        if log_names != [f"shard_{index}.log" for index in range(SHARD_COUNT)]:
            raise ValueError(f"canary log set mismatch: {log_names}")

        starts: list[int] = []
        finishes: list[int] = []
        scratch_dirs: set[str] = set()
        record_hashes: dict[str, str] = {}
        for shard_index, arm in enumerate(CANARY_ARMS):
            path = record_dir / f"canary_{shard_index}.json"
            record = formal._load_json(path)
            expected_fields = {
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "phase": "r338-three-worker-physical-canary",
                "controller": arm,
                "formal_seal_sha256": expected,
                "formal_bank_sha256": manifest["formal_bank"]["sha256"],
                "execution_shard_index": shard_index,
                "execution_shard_count": SHARD_COUNT,
                "observed_concurrent_workers": SHARD_COUNT,
                "performance_use": "forbidden",
            }
            for key, value in expected_fields.items():
                if record.get(key) != value:
                    raise ValueError(f"canary provenance mismatch in {path}: {key}")
            if not record.get("completed") or record.get("tds_failed"):
                raise ValueError(f"canary worker did not complete: {path}")
            if int(record.get("requested_steps", -1)) != CANARY_STEPS:
                raise ValueError(f"canary step budget drift: {path}")
            starts.append(int(record["simulation_started_ns"]))
            finishes.append(int(record["simulation_finished_ns"]))
            scratch_dirs.add(str(record["scratch_working_directory"]))
            record_hashes[str(path.relative_to(ROOT)).replace("\\", "/")] = (
                formal.sha256_file(path)
            )

        if len(scratch_dirs) != SHARD_COUNT:
            raise ValueError(f"canary scratch directories collided: {scratch_dirs}")
        if max(starts) >= min(finishes):
            raise ValueError("three physical canary simulations did not overlap")

        payload = {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "classification": "PASS",
            "formal_seal_sha256": expected,
            "formal_bank_sha256": manifest["formal_bank"]["sha256"],
            "worker_count": SHARD_COUNT,
            "unique_scratch_directory_count": len(scratch_dirs),
            "physical_simulation_overlap": True,
            "completed_record_count": SHARD_COUNT,
            "record_hashes": dict(sorted(record_hashes.items())),
            "performance_endpoints_inspected": False,
            "automatic_formal_release": False,
            "next_gate": "await-explicit-full-formal-continuation",
        }
        return formal._write_new(gate_path, payload)


def _require_canary_pass(expected: str, gate_path: Path = CANARY_GATE) -> None:
    gate = _load_hashed_json(gate_path)
    if gate.get("classification") != "PASS":
        raise ValueError("R338 full formal execution requires a passing canary")
    if gate.get("formal_seal_sha256") != expected:
        raise ValueError("R338 canary belongs to a different formal seal")
    if gate.get("automatic_formal_release") is not False:
        raise ValueError("R338 canary release contract drift")


def run_formal_shard(
    manifest_path: Path,
    expected: str,
    out_dir: Path,
    shard_index: int,
    shard_count: int,
) -> None:
    _require_canary_pass(expected)
    with _configured_formal() as formal:
        _formal_run_shard(
            formal, manifest_path, expected, out_dir, shard_index, shard_count
        )


def analyse(manifest_path: Path, expected: str, out_dir: Path) -> None:
    _require_canary_pass(expected)
    with _configured_formal() as formal:
        formal.analyse(manifest_path, expected, out_dir)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--manifest", type=Path, default=FORMAL_SEAL)
    prepare_parser.add_argument("--out-dir", type=Path, default=FORMAL_OUT)

    canary_parser = subparsers.add_parser("canary-worker")
    canary_parser.add_argument("--manifest", type=Path, default=FORMAL_SEAL)
    canary_parser.add_argument("--expected-manifest-sha256", required=True)
    canary_parser.add_argument("--out-dir", type=Path, default=CANARY_RECORD_DIR)
    canary_parser.add_argument("--barrier-dir", type=Path, default=CANARY_BARRIER_DIR)
    canary_parser.add_argument("--barrier-timeout-seconds", type=float, default=30.0)
    canary_parser.add_argument("--shard-index", type=int, required=True)
    canary_parser.add_argument("--shard-count", type=int, default=SHARD_COUNT)

    verify_parser = subparsers.add_parser("verify-canary")
    verify_parser.add_argument("--manifest", type=Path, default=FORMAL_SEAL)
    verify_parser.add_argument("--expected-manifest-sha256", required=True)
    verify_parser.add_argument("--canary-dir", type=Path, default=CANARY_OUT)
    verify_parser.add_argument("--log-dir", type=Path, default=CANARY_LOG_DIR)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--manifest", type=Path, default=FORMAL_SEAL)
    run_parser.add_argument("--expected-manifest-sha256", required=True)
    run_parser.add_argument("--out-dir", type=Path, default=FORMAL_OUT)
    run_parser.add_argument("--shard-index", type=int, required=True)
    run_parser.add_argument("--shard-count", type=int, default=SHARD_COUNT)

    analyse_parser = subparsers.add_parser("analyse")
    analyse_parser.add_argument("--manifest", type=Path, default=FORMAL_SEAL)
    analyse_parser.add_argument("--expected-manifest-sha256", required=True)
    analyse_parser.add_argument("--out-dir", type=Path, default=FORMAL_OUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "prepare":
        prepare(args.manifest, args.out_dir)
    elif args.command == "canary-worker":
        run_canary_worker(
            args.manifest,
            args.expected_manifest_sha256,
            args.out_dir,
            args.barrier_dir,
            args.shard_index,
            args.shard_count,
            args.barrier_timeout_seconds,
        )
    elif args.command == "verify-canary":
        digest = verify_canary(
            args.manifest,
            args.expected_manifest_sha256,
            args.canary_dir,
            args.log_dir,
        )
        print(f"[canary-pass] sha256={digest}", flush=True)
    elif args.command == "run":
        run_formal_shard(
            args.manifest,
            args.expected_manifest_sha256,
            args.out_dir,
            args.shard_index,
            args.shard_count,
        )
    else:
        analyse(args.manifest, args.expected_manifest_sha256, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
