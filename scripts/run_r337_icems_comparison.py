#!/usr/bin/env python3
"""Prospective R337 ICEMS architecture-comparison entrypoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import traceback
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

ROUND_ID = "R337"
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
R293_GUARD_SUMMARY = ROOT / "results/r293_classical_guard/classical_guard_summary.json"
R293_GUARD_PROVENANCE = ROOT / "results/r293_classical_guard/provenance.json"
TRAINING_SEAL = ROOT / "memory/rounds/R337/training_seal.json"
TRAINING_OUT = ROOT / "results/r337_prior_residual_training"
REHEARSAL_RECORD = ROOT / "memory/rounds/R337/rehearsal.json"
FRESH_SEAL = ROOT / "memory/rounds/R337/fresh_bank_screen_seal.json"
FRESH_OUT = ROOT / "results/r337_fresh_bank"
FORMAL_SEAL = ROOT / "memory/rounds/R337/formal_seal.json"
FORMAL_OUT = ROOT / "results/r337_formal_evaluation"
FORMAL_ATTEMPT = ROOT / "memory/rounds/R337/formal_attempt.json"
FORMAL_FAILURE = ROOT / "memory/rounds/R337/formal_failure.json"
EXECUTION_RECORD = ROOT / "memory/rounds/R337/execution_complete.json"
PIPELINE_OUT = ROOT / "results/r337_pipeline"


def build_contract() -> dict[str, Any]:
    """Return the public, outcome-independent R337 comparison contract."""

    distributed_parameters = 4_929
    single_actor_parameters = 4_959
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "question": QUESTION_ID,
        "title": TITLE,
        "title_changed": False,
        "seeds": list(SEEDS),
        "distributed_execution": {
            "information": "two_endpoints_per_edge",
            "outputs": 3,
            "runtime_central_aggregation": False,
            "training_only_central_critic": True,
        },
        "single_actor_execution": {
            "information": "joint_20d",
            "outputs": 3,
        },
        "matched": {
            "action_coordinates": "three_oriented_path_edges",
            "actor_parameter_counts": {
                "distributed": distributed_parameters,
                "single_actor": single_actor_parameters,
            },
            "actor_parameter_relative_difference": abs(
                single_actor_parameters - distributed_parameters
            )
            / distributed_parameters,
            "training_episodes_per_seed": 300,
            "steps_per_episode": 15,
            "candidate_bank_seed": 2026080401,
            "bootstrap_seed": 2026080402,
        },
        "excluded_r293_assets": [
            "checkpoints",
            "replay_buffers",
            "training_diagnostics",
            "candidate_bank",
            "screen_records",
            "formal_traces",
            "formal_outcomes",
        ],
        "formal_launch": {
            "rehearsal_scope": "same-pre-attempt-path",
            "rehearsal_checks": [
                "source_hash",
                "parent_hash",
                "installed_package",
                "installed_case",
                "output_absence",
            ],
            "wsl_python_processes": 3,
            "native_threads_per_process": 1,
        },
    }


def build_stage_contract() -> dict[str, Any]:
    """Expose the create-only R337 stage routing used by the formal entry."""

    return {
        "training": {
            "seal": "memory/rounds/R337/training_seal.json",
            "out": "results/r337_prior_residual_training",
            "run_count": 10,
        },
        "fresh_bank": {
            "seal": "memory/rounds/R337/fresh_bank_screen_seal.json",
            "out": "results/r337_fresh_bank",
            "candidate_seed": 2026080401,
            "scenario_count": 24,
        },
        "formal": {
            "seal": "memory/rounds/R337/formal_seal.json",
            "out": "results/r337_formal_evaluation",
            "arm_count": 12,
            "matrix_count": 288,
            "bootstrap_seed": 2026080402,
        },
        "viewed_parent_only": {
            "classical_guard_summary": (
                "results/r293_classical_guard/classical_guard_summary.json"
            ),
            "classical_guard_provenance": (
                "results/r293_classical_guard/provenance.json"
            ),
        },
        "execution": {
            "serial_in_one_formal_child": True,
            "maximum_r337_wsl_python_processes": 3,
            "native_threads_per_process": 1,
            "automatic_retry": False,
        },
    }


def _training_source_paths() -> dict[str, Path]:
    paths = {
        "plan": ROOT / "memory/rounds/R337/plan.md",
        "question": ROOT / "memory/questions/Q-0088.md",
        "r337_adapter": Path(__file__).resolve(),
        "r337_tests": ROOT / "tests/test_r337_icems_comparison.py",
        "inherited_training_core": ROOT / "scripts/train_r293_prior_residual.py",
        "prior_agents": ROOT / "src/andes_rl_kundur/agents/classical_prior_td3.py",
        "vector_agents": ROOT / "src/andes_rl_kundur/agents/vector_residual_td3.py",
        "classical_controller": ROOT
        / "src/andes_rl_kundur/control/classical_edge_residual.py",
        "vector_contract": ROOT
        / "src/andes_rl_kundur/control/vector_inertia_residual.py",
        "prior_environment": ROOT
        / "src/andes_rl_kundur/env/andes/prior_residual_env.py",
        "vector_environment": ROOT
        / "src/andes_rl_kundur/env/andes/distributed_residual_env.py",
        "development_bank": ROOT
        / "results/r274_prospective_active_power_authority/formal_bank.json",
        "classical_guard_summary": R293_GUARD_SUMMARY,
        "classical_guard_provenance": R293_GUARD_PROVENANCE,
    }
    if REHEARSAL_RECORD.is_file():
        paths["rehearsal_record"] = REHEARSAL_RECORD
    return paths


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _source_paths() -> dict[str, Path]:
    paths = _training_source_paths()
    paths.pop("rehearsal_record", None)
    paths.update(
        {
            "inherited_fresh_adapter": ROOT / "scripts/run_r293_fresh_bank.py",
            "inherited_fresh_core": ROOT / "scripts/run_r292_fresh_bank.py",
            "inherited_formal_core": ROOT / "scripts/run_r293_formal.py",
            "decision_probe": ROOT / "probes/r293_comparison.py",
            "scratch_launcher": ROOT / "scripts/andes_scratch.py",
            "vector_runner": ROOT
            / "src/andes_rl_kundur/evaluation/vector_residual.py",
            "screen_record_audit": ROOT
            / "src/andes_rl_kundur/evaluation/r292_screen.py",
            "screen_bank_audit": ROOT
            / "src/andes_rl_kundur/evaluation/r292_screen_bank.py",
            "prospective_authority": ROOT
            / "src/andes_rl_kundur/evaluation/prospective_authority.py",
            "sealed_bank": ROOT / "src/andes_rl_kundur/evaluation/sealed_bank.py",
        }
    )
    return paths


def _parent_paths() -> dict[str, Path]:
    return {
        "r293_classical_development_summary": ROOT
        / "results/r293_classical_development/classical_development_summary.json",
        "r293_classical_development_provenance": ROOT
        / "results/r293_classical_development/provenance.json",
        "r293_classical_guard_summary": R293_GUARD_SUMMARY,
        "r293_classical_guard_provenance": R293_GUARD_PROVENANCE,
        "r293_plan": ROOT / "memory/rounds/R293/plan.md",
        "r292_claim": ROOT / "memory/claims/CLM-0675.md",
        "r293_question": ROOT / "memory/questions/Q-0050.md",
    }


def _verified_hashes(paths: dict[str, Path], *, require_sidecars: bool) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(path)
        digest = _sha256_file(path)
        sidecar = path.with_name(path.name + ".sha256")
        if require_sidecars and path.suffix == ".json":
            if not sidecar.is_file():
                raise FileNotFoundError(sidecar)
            expected = sidecar.read_text(encoding="utf-8").split()[0].lower()
            if expected != digest:
                raise ValueError(f"parent hash sidecar mismatch: {path}")
        hashes[name] = digest
    return hashes


def _installed_andes_identity() -> dict[str, Any]:
    from scripts import run_r334_pq_disturbance_identification as r334

    return r334._verify_installed_andes()


def _r337_python_process_count() -> int:
    if os.name == "nt":
        return 0
    count = 0
    proc = Path("/proc")
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            command = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(
                "utf-8", errors="replace"
            )
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if "python" in command and "run_r337_icems_comparison.py" in command:
            count += 1
    return count


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
        EXECUTION_RECORD,
        PIPELINE_OUT,
    ]


def pre_attempt_checks(*, output_paths: list[Path] | None = None) -> dict[str, Any]:
    """Run the common rehearsal/execute checks before any attempt is created."""

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
        raise FileExistsError(f"pre-existing R337 formal asset: {rendered}")
    process_count = _r337_python_process_count()
    if process_count > 3:
        raise RuntimeError(f"R337 WSL Python process cap exceeded: {process_count} > 3")
    thread_values = {name: os.environ.get(name) for name in _THREAD_ENVIRONMENT}
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
    actual = _sha256_file(path)
    if actual != expected:
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
    """Persist the create-only same-path launch rehearsal."""

    checks = pre_attempt_checks(output_paths=output_paths)
    payload = {
        **checks,
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
    """Rerun the rehearsal path and reject any identity or runtime drift."""

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
def _configured_training():
    from scripts import train_r293_prior_residual as base

    replacements = {
        "ROUND_ID": ROUND_ID,
        "QUESTION_ID": QUESTION_ID,
        "SEEDS": SEEDS,
        "GUARD_SUMMARY": R293_GUARD_SUMMARY,
        "GUARD_PROVENANCE": R293_GUARD_PROVENANCE,
        "DEFAULT_SEAL": TRAINING_SEAL,
        "DEFAULT_OUT": TRAINING_OUT,
        "_source_paths": _training_source_paths,
    }
    previous = {name: getattr(base, name) for name in replacements}
    for name, value in replacements.items():
        setattr(base, name, value)
    try:
        yield base
    finally:
        for name, value in previous.items():
            setattr(base, name, value)


def prepare_training_seal(manifest_path: Path, out_root: Path) -> None:
    """Create the R337 training seal through the inherited frozen runner."""

    with _configured_training() as training:
        training.prepare(manifest_path, out_root)


def _fresh_source_paths() -> dict[str, Path]:
    paths = {
        "plan": ROOT / "memory/rounds/R337/plan.md",
        "question": ROOT / "memory/questions/Q-0088.md",
        "r337_adapter": Path(__file__).resolve(),
        "r337_tests": ROOT / "tests/test_r337_icems_comparison.py",
        "rehearsal_record": REHEARSAL_RECORD,
        "inherited_fresh_adapter": ROOT / "scripts/run_r293_fresh_bank.py",
        "inherited_fresh_core": ROOT / "scripts/run_r292_fresh_bank.py",
        "vector_runner": ROOT / "src/andes_rl_kundur/evaluation/vector_residual.py",
        "screen_record_audit": ROOT
        / "src/andes_rl_kundur/evaluation/r292_screen.py",
        "screen_bank_audit": ROOT
        / "src/andes_rl_kundur/evaluation/r292_screen_bank.py",
        "prospective_authority": ROOT
        / "src/andes_rl_kundur/evaluation/prospective_authority.py",
        "sealed_bank": ROOT / "src/andes_rl_kundur/evaluation/sealed_bank.py",
        "training_summary": TRAINING_OUT / "training_matrix_summary.json",
        "reference_bank": ROOT
        / "results/r274_prospective_active_power_authority/formal_bank.json",
    }
    return paths


@contextmanager
def _configured_fresh():
    from scripts import run_r293_fresh_bank as adapter

    core = adapter.CORE
    replacements = {
        "ROUND_ID": ROUND_ID,
        "QUESTION_ID": QUESTION_ID,
        "CANDIDATE_SEED": 2026080401,
        "TRAINING_SUMMARY": TRAINING_OUT / "training_matrix_summary.json",
        "DEFAULT_SEAL": FRESH_SEAL,
        "DEFAULT_OUT": FRESH_OUT,
        "FORMAL_TRACE_DIR": FORMAL_OUT / "traces",
        "_verify_training": adapter._verify_training,
        "_source_paths": _fresh_source_paths,
    }
    previous = {name: getattr(core, name) for name in replacements}
    for name, value in replacements.items():
        setattr(core, name, value)
    try:
        yield core
    finally:
        for name, value in previous.items():
            setattr(core, name, value)


def _checkpoint_path(architecture: str, seed: int) -> Path:
    return TRAINING_OUT / f"{architecture}_s{seed}" / "final.pt"


def _controller_contract_path(architecture: str, seed: int) -> Path:
    return TRAINING_OUT / f"{architecture}_s{seed}" / "controller_contract.json"


def _formal_source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R337/plan.md",
        "question": ROOT / "memory/questions/Q-0088.md",
        "r337_adapter": Path(__file__).resolve(),
        "r337_tests": ROOT / "tests/test_r337_icems_comparison.py",
        "rehearsal_record": REHEARSAL_RECORD,
        "inherited_formal_core": ROOT / "scripts/run_r293_formal.py",
        "decision_probe": ROOT / "probes/r293_comparison.py",
        "vector_runner": ROOT / "src/andes_rl_kundur/evaluation/vector_residual.py",
        "sealed_bank": ROOT / "src/andes_rl_kundur/evaluation/sealed_bank.py",
        "prior_actor": ROOT / "src/andes_rl_kundur/agents/classical_prior_td3.py",
        "vector_actor": ROOT / "src/andes_rl_kundur/agents/vector_residual_td3.py",
        "classical_controller": ROOT
        / "src/andes_rl_kundur/control/classical_edge_residual.py",
        "vector_environment": ROOT
        / "src/andes_rl_kundur/env/andes/distributed_residual_env.py",
        "prior_environment": ROOT
        / "src/andes_rl_kundur/env/andes/prior_residual_env.py",
        "vector_contract": ROOT
        / "src/andes_rl_kundur/control/vector_inertia_residual.py",
        "formal_bank": FRESH_OUT / "formal_bank.json",
        "screen_summary": FRESH_OUT / "screen_summary.json",
        "screen_contract": FRESH_OUT / "feasibility_screen_contract.json",
        "screen_provenance": FRESH_OUT / "provenance.json",
        "training_summary": TRAINING_OUT / "training_matrix_summary.json",
        "classical_guard": R293_GUARD_SUMMARY,
    }


@contextmanager
def _configured_formal():
    from scripts import run_r293_formal as base

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
        "FRESH_DIR": FRESH_OUT,
        "FORMAL_BANK": FRESH_OUT / "formal_bank.json",
        "SCREEN_SUMMARY": FRESH_OUT / "screen_summary.json",
        "SCREEN_CONTRACT": FRESH_OUT / "feasibility_screen_contract.json",
        "SCREEN_PROVENANCE": FRESH_OUT / "provenance.json",
        "TRAINING_SUMMARY": TRAINING_OUT / "training_matrix_summary.json",
        "CLASSICAL_GUARD": R293_GUARD_SUMMARY,
        "DEFAULT_SEAL": FORMAL_SEAL,
        "DEFAULT_OUT": FORMAL_OUT,
        "_checkpoint_path": _checkpoint_path,
        "_contract_path": _controller_contract_path,
        "_source_paths": _formal_source_paths,
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
    digest = sidecar.read_text(encoding="utf-8").split()[0].lower()
    if digest != _sha256_file(path):
        raise ValueError(f"artifact sidecar mismatch: {path}")
    return digest


def _run_training_stage() -> None:
    prepare_training_seal(TRAINING_SEAL, TRAINING_OUT)
    seal_digest = _artifact_digest(TRAINING_SEAL)
    with _configured_training() as training:
        for architecture in training.ARCHITECTURES:
            for seed in SEEDS:
                return_code = training.train(
                    TRAINING_SEAL,
                    seal_digest,
                    TRAINING_OUT,
                    architecture,
                    seed,
                    "cpu",
                    None,
                )
                if return_code != 0:
                    raise RuntimeError(
                        f"retained training failure: {architecture} seed {seed}"
                    )
        training.verify_matrix(TRAINING_SEAL, seal_digest, TRAINING_OUT)


def _run_fresh_stage() -> None:
    with _configured_fresh() as fresh:
        fresh.prepare(FRESH_SEAL, FRESH_OUT)
        seal_digest = _artifact_digest(FRESH_SEAL)
        for shard_index in range(fresh.SHARD_COUNT):
            fresh.run_shard(
                FRESH_SEAL,
                seal_digest,
                FRESH_OUT,
                shard_index,
                fresh.SHARD_COUNT,
            )
        fresh.analyse(FRESH_SEAL, seal_digest, FRESH_OUT)


def _run_formal_stage() -> None:
    with _configured_formal() as formal:
        formal.prepare(FORMAL_SEAL, FORMAL_OUT)
        seal_digest = _artifact_digest(FORMAL_SEAL)
        for shard_index in range(formal.SHARD_COUNT):
            formal.run_shard(
                FORMAL_SEAL,
                seal_digest,
                FORMAL_OUT,
                shard_index,
                formal.SHARD_COUNT,
            )
        formal.analyse(FORMAL_SEAL, seal_digest, FORMAL_OUT)


def execute() -> str:
    """Run the single create-only R337 formal attempt from rehearsal to result."""

    verification = verify_rehearsal()
    rehearsal_digest = _artifact_digest(REHEARSAL_RECORD)
    attempt_digest = _write_new_json(
        FORMAL_ATTEMPT,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "phase": "formal-attempt",
            "attempt_number": 1,
            "rehearsal_sha256": rehearsal_digest,
            "verification": verification,
            "automatic_retry": False,
        },
    )
    try:
        _run_training_stage()
        _run_fresh_stage()
        _run_formal_stage()
        formal_summary = FORMAL_OUT / "formal_summary.json"
        payload = {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "phase": "formal-execution-complete",
            "attempt_sha256": attempt_digest,
            "training_summary_sha256": _artifact_digest(
                TRAINING_OUT / "training_matrix_summary.json"
            ),
            "fresh_screen_summary_sha256": _artifact_digest(
                FRESH_OUT / "screen_summary.json"
            ),
            "formal_summary_sha256": _artifact_digest(formal_summary),
            "automatic_retry": False,
        }
        digest = _write_new_json(EXECUTION_RECORD, payload)
        status = PIPELINE_OUT / "status" / "complete"
        status.parent.mkdir(parents=True, exist_ok=True)
        status.write_text(f"{digest}\n", encoding="utf-8")
        return digest
    except BaseException as error:
        if not FORMAL_FAILURE.exists():
            _write_new_json(
                FORMAL_FAILURE,
                {
                    "schema_version": 1,
                    "round": ROUND_ID,
                    "question": QUESTION_ID,
                    "phase": "formal-attempt-failure",
                    "attempt_sha256": attempt_digest,
                    "error_type": type(error).__name__,
                    "error": str(error),
                    "traceback": traceback.format_exc(),
                    "automatic_retry": False,
                },
            )
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("rehearse")
    subparsers.add_parser("execute")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "rehearse":
        digest = rehearse()
        print(f"[rehearsed] sha256={digest}", flush=True)
        return 0
    digest = execute()
    print(f"[completed] sha256={digest}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
