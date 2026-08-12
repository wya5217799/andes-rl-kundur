"""Output-safe sealed successor for the R367 deterministic-headroom gate."""

from __future__ import annotations

import os

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"
os.environ["DISABLE_TOGGLER"] = "1"

import argparse
from datetime import UTC, datetime
from pathlib import Path
import shutil
import sys
import time
from typing import Any, Mapping, TextIO

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

import scripts.run_r367_deterministic_headroom as parent


ROUND_ID = "R368"
QUESTION_ID = "Q-0103"
PLAN = ROOT / "memory/rounds/R368/plan.md"
QUESTION = ROOT / "memory/questions/Q-0103.md"
REHEARSAL = ROOT / "memory/rounds/R368/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R368/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R368/formal_seal.json"
DEFAULT_OUT = ROOT / "results/research_loop/r368_deterministic_headroom"


def safe_emit(message: str, *, stream: TextIO | None = None) -> bool:
    """Best-effort console output that can never invalidate the run."""

    target = sys.stdout if stream is None else stream
    try:
        print(message, file=target, flush=True)
    except BrokenPipeError:
        if stream is None:
            sys.stdout = open(os.devnull, "w", encoding="utf-8")
        return False
    return True


def build_successor_contract() -> dict[str, Any]:
    """Return the byte-equivalent R367 scientific contract."""

    return parent.build_contract()


def _source_manifest() -> dict[str, dict[str, str]]:
    sources = {
        "successor_runner": Path(__file__).resolve(),
        "successor_tests": ROOT / "tests/test_r368_deterministic_headroom.py",
        "parent_runner": ROOT / "scripts/run_r367_deterministic_headroom.py",
        "classifier": ROOT
        / "src/andes_rl_kundur/evaluation/deterministic_headroom.py",
        "controller": ROOT / "src/andes_rl_kundur/control/per_vsg_md.py",
        "classifier_tests": ROOT / "tests/test_deterministic_headroom.py",
        "parent_runner_tests": ROOT / "tests/test_r367_deterministic_headroom.py",
        "plan": PLAN,
        "question": QUESTION,
        "line": ROOT / "paper/paralleled_vsg_marl/LINE.md",
        "route": ROOT / "paper/paralleled_vsg_marl/ROUTE.md",
        "v4_environment": ROOT
        / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
        "v4_config": ROOT / "src/andes_rl_kundur/env/andes/v4_config.py",
        "base_environment": ROOT / "src/andes_rl_kundur/env/andes/base_env.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "dependencies": ROOT / "pyproject.toml",
    }
    return {
        name: {"path": parent._relative(path), "sha256": parent._sha256_file(path)}
        for name, path in sources.items()
    }


def _parent_manifest() -> dict[str, dict[str, str]]:
    parents = {
        "r367_attempt": ROOT
        / "results/research_loop/r367_deterministic_headroom/formal_attempt.json",
        "r367_failure": ROOT
        / "results/research_loop/r367_deterministic_headroom/formal_failure.json",
        "r367_seal": ROOT / "memory/rounds/R367/formal_seal.json",
        "design_claim": ROOT / "memory/claims/CLM-0980.md",
        "design_feed": ROOT / "paper/paralleled_vsg_marl/reports/R366.md",
        "scenario_source": ROOT
        / "results/r274_prospective_active_power_authority/formal_bank.json",
    }
    return {
        name: {"path": parent._relative(path), "sha256": parent._sha256_file(path)}
        for name, path in parents.items()
    }


def _assert_parent_contract() -> dict[str, Any]:
    contract = build_successor_contract()
    r367_seal = parent._read_hashed_json(ROOT / "memory/rounds/R367/formal_seal.json")
    if r367_seal.get("contract") != contract:
        raise RuntimeError("R367 scientific contract drift")
    if r367_seal.get("contract_sha256") != parent._payload_sha256(contract):
        raise RuntimeError("R367 scientific contract hash mismatch")
    failure = parent._read_hashed_json(
        ROOT / "results/research_loop/r367_deterministic_headroom/formal_failure.json"
    )
    if failure.get("error_type") != "BrokenPipeError":
        raise RuntimeError("R368 parent failure is not the registered output-pipe failure")
    return contract


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("R368 physical/rehearsal commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R368 must run through scripts/andes_scratch.py")


def rehearse(path: Path = REHEARSAL) -> str:
    _assert_wsl_scratch()
    collisions = [candidate for candidate in (path, CAPACITY, SEAL, DEFAULT_OUT) if candidate.exists()]
    if collisions:
        raise FileExistsError(f"R368 pre-attempt artifact exists: {collisions}")
    runtime = parent._installed_runtime()
    contract = _assert_parent_contract()
    checks = {
        "source_hash": bool(_source_manifest()),
        "parent_hash": bool(_parent_manifest()),
        "installed_package": runtime["andes_version"] != "unknown",
        "installed_case": Path(runtime["case_path"]).is_file(),
        "output_absence": not DEFAULT_OUT.exists() and not SEAL.exists(),
        "active_plan": "state: active" in PLAN.read_text(encoding="utf-8")
        and "manuscript_line: paralleled-vsg-marl" in PLAN.read_text(encoding="utf-8"),
        "in_flight_question": "status: in-flight"
        in QUESTION.read_text(encoding="utf-8"),
        "contract_closed": len(contract["scenarios"]) == 8
        and len(contract["arm_ids"]) == 10
        and contract["training_authorized"] is False,
        "output_safe_seam": safe_emit("", stream=open(os.devnull, "w")),
        "physical_trajectory_executed": False,
    }
    return parent._write_new_json(
        path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "scientific_contract_round": "R367",
            "contract_sha256": parent._payload_sha256(contract),
            "sources": _source_manifest(),
            "parents": _parent_manifest(),
            "installed_runtime": runtime,
            "checks": checks,
            "formal_authority": False,
            "training_executed": False,
        },
    )


def _build_capacity_payload(
    *,
    representative_valid: bool,
    representative_wall_seconds: float,
    max_rss_kib: int,
    disk_free_bytes: int,
    logical_processors: int,
    physical_memory_bytes: int,
    wsl_memory_available_bytes: int,
    runtime: Mapping[str, Any],
    sources: Mapping[str, Any],
    parents: Mapping[str, Any],
) -> dict[str, Any]:
    contract = build_successor_contract()
    jobs = len(contract["scenarios"]) * len(contract["arm_ids"])
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "readiness": "RUN-READY" if representative_valid else "HOLD",
        "whole_host_python_process_budget": 1,
        "host": {
            "logical_processors": int(logical_processors),
            "physical_memory_bytes": int(physical_memory_bytes),
        },
        "wsl": {"memory_available_bytes": int(wsl_memory_available_bytes)},
        "empirical_anchor": {
            "all_records_valid": bool(representative_valid),
            "concurrent_workers": 1,
            "native_threads_per_worker": 1,
            "representative_steps": 5,
            "wall_seconds": float(representative_wall_seconds),
        },
        "representative_steps": 5,
        "representative_wall_seconds": float(representative_wall_seconds),
        "projected_formal_wall_seconds": float(representative_wall_seconds)
        * (jobs * int(contract["steps"]) / 5.0),
        "max_rss_kib": int(max_rss_kib),
        "disk_free_bytes": int(disk_free_bytes),
        "host_process_budget": 1,
        "wsl_python_processes": 1,
        "native_threads_per_process": 1,
        "other_reserved_processes": 0,
        "other_processes": [],
        "installed_runtime": dict(runtime),
        "sources": dict(sources),
        "parents": dict(parents),
        "scientific_classification_inspected": False,
        "formal_authority": False,
        "training_executed": False,
    }


def measure_capacity(path: Path = CAPACITY) -> str:
    import resource

    _assert_wsl_scratch()
    rehearsal = parent._read_hashed_json(REHEARSAL)
    if not parent._rehearsal_checks(rehearsal):
        raise RuntimeError("R368 rehearsal did not pass")
    if rehearsal["sources"] != _source_manifest() or rehearsal["parents"] != _parent_manifest():
        raise RuntimeError("R368 source or parent drift after rehearsal")
    if path.exists() or SEAL.exists() or DEFAULT_OUT.exists():
        raise FileExistsError("R368 capacity/seal/formal artifact collision")
    other = parent._other_research_python_processes()
    if other:
        raise RuntimeError(f"other research Python processes are active: {other}")
    scenario = _assert_parent_contract()["scenarios"][0]
    started = time.perf_counter()
    representative = parent._run_scenario_arm(scenario, "zero", steps_override=5)
    wall_seconds = time.perf_counter() - started
    valid = bool(representative["completed"] and not representative["tds_failed"])
    usage = resource.getrusage(resource.RUSAGE_SELF)
    disk = shutil.disk_usage(ROOT)
    logical, physical_memory, wsl_available = parent._memory_resources()
    payload = _build_capacity_payload(
        representative_valid=valid,
        representative_wall_seconds=wall_seconds,
        max_rss_kib=int(usage.ru_maxrss),
        disk_free_bytes=int(disk.free),
        logical_processors=logical,
        physical_memory_bytes=physical_memory,
        wsl_memory_available_bytes=wsl_available,
        runtime=parent._installed_runtime(),
        sources=_source_manifest(),
        parents=_parent_manifest(),
    )
    payload["other_processes"] = other
    return parent._write_new_json(path, payload)


def prepare(path: Path = SEAL) -> str:
    rehearsal = parent._read_hashed_json(REHEARSAL)
    capacity = parent._read_hashed_json(CAPACITY)
    if not parent._rehearsal_checks(rehearsal):
        raise RuntimeError("R368 rehearsal did not pass")
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R368 capacity gate is not RUN-READY")
    if rehearsal["sources"] != _source_manifest() or capacity["sources"] != _source_manifest():
        raise RuntimeError("R368 source drift before sealing")
    if rehearsal["parents"] != _parent_manifest() or capacity["parents"] != _parent_manifest():
        raise RuntimeError("R368 parent drift before sealing")
    if rehearsal["installed_runtime"] != parent._installed_runtime():
        raise RuntimeError("R368 installed runtime drift before sealing")
    if DEFAULT_OUT.exists():
        raise FileExistsError("R368 formal output exists before sealing")
    contract = _assert_parent_contract()
    return parent._write_new_json(
        path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "scientific_contract_round": "R367",
            "contract": contract,
            "contract_sha256": parent._payload_sha256(contract),
            "sources": _source_manifest(),
            "parents": _parent_manifest(),
            "installed_runtime": parent._installed_runtime(),
            "rehearsal_sha256": parent._sha256_file(REHEARSAL),
            "capacity_sha256": parent._sha256_file(CAPACITY),
            "launch": {
                "host_process_budget": 1,
                "wsl_python_processes": 1,
                "native_threads_per_process": 1,
                "other_reserved_processes": 0,
            },
            "formal_artifacts_create_only": True,
            "retry_authorized": False,
            "training_authorized": False,
        },
    )


def _load_seal(expected_sha256: str) -> tuple[dict[str, Any], str]:
    seal = parent._read_hashed_json(SEAL)
    digest = parent._sha256_file(SEAL)
    if digest != expected_sha256:
        raise RuntimeError("R368 seal digest mismatch")
    if seal.get("contract") != _assert_parent_contract():
        raise RuntimeError("R368 contract drift")
    if seal.get("sources") != _source_manifest() or seal.get("parents") != _parent_manifest():
        raise RuntimeError("R368 sealed source or parent drift")
    if seal.get("installed_runtime") != parent._installed_runtime():
        raise RuntimeError("R368 sealed runtime drift")
    if seal.get("capacity_sha256") != parent._sha256_file(CAPACITY):
        raise RuntimeError("R368 capacity drift")
    return seal, digest


def execute(*, expected_sha256: str, out_dir: Path = DEFAULT_OUT) -> str:
    _assert_wsl_scratch()
    seal, seal_digest = _load_seal(expected_sha256)
    other = parent._other_research_python_processes()
    if other:
        raise RuntimeError(f"other research Python processes are active: {other}")
    if out_dir.exists():
        raise FileExistsError(f"R368 output collision: {out_dir}")
    attempt_digest = parent._write_new_json(
        out_dir / "formal_attempt.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "retry_authorized": False,
            "training_authorized": False,
        },
    )
    started = time.perf_counter()
    try:
        records = [
            parent._run_scenario_arm(scenario, arm_id)
            for scenario in seal["contract"]["scenarios"]
            for arm_id in seal["contract"]["arm_ids"]
        ]
        execution = {
            "schema_version": 1,
            "round": ROUND_ID,
            "question": QUESTION_ID,
            "scientific_contract_round": "R367",
            "seal_sha256": seal_digest,
            "attempt_sha256": attempt_digest,
            "wall_seconds": time.perf_counter() - started,
            "record_count": len(records),
            "records": records,
            "reward_used_for_gate": False,
            "training_executed": False,
        }
        execution_digest = parent._write_new_json(
            out_dir / "formal_execution.json", execution
        )
        summaries = [
            parent.summarise_record(record, contract=seal["contract"])
            for record in records
        ]
        analysis = parent.classify_summaries(summaries, contract=seal["contract"])
        analysis.update(
            {
                "round": ROUND_ID,
                "scientific_contract_round": "R367",
                "summaries": summaries,
                "seal_sha256": seal_digest,
                "formal_execution_sha256": execution_digest,
                "training_authorized": False,
            }
        )
        analysis_digest = parent._write_new_json(
            out_dir / "formal_analysis.json", analysis
        )
        parent._write_new_json(
            out_dir / "formal_manifest.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "entries": [
                    {"path": parent._relative(out_dir / "formal_attempt.json"), "sha256": attempt_digest},
                    {"path": parent._relative(out_dir / "formal_execution.json"), "sha256": execution_digest},
                    {"path": parent._relative(out_dir / "formal_analysis.json"), "sha256": analysis_digest},
                ],
            },
        )
        safe_emit(f"classification={analysis['classification']}")
        return analysis_digest
    except Exception as exc:
        parent._write_new_json(
            out_dir / "formal_failure.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "question": QUESTION_ID,
                "seal_sha256": seal_digest,
                "attempt_sha256": attempt_digest,
                "classification": "ANALYSIS-INVALID",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "wall_seconds": time.perf_counter() - started,
                "retry_authorized": False,
                "training_authorized": False,
            },
        )
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("rehearse")
    commands.add_parser("measure-capacity")
    commands.add_parser("prepare")
    formal = commands.add_parser("execute")
    formal.add_argument("--expected-seal-sha256", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "rehearse":
        safe_emit(f"rehearsal_sha256={rehearse()}")
    elif args.command == "measure-capacity":
        safe_emit(f"capacity_sha256={measure_capacity()}")
    elif args.command == "prepare":
        safe_emit(f"seal_sha256={prepare()}")
    elif args.command == "execute":
        safe_emit(f"analysis_sha256={execute(expected_sha256=args.expected_seal_sha256)}")
    else:  # pragma: no cover
        raise RuntimeError(f"unknown command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
