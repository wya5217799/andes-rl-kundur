#!/usr/bin/env python3
"""R378 correction round: reanalyse immutable R377 development, then hold out.

Usage (WSL):
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r378_gate_b2_correction.py rehearse
    /home/wya/andes_venv/bin/python scripts/run_r378_gate_b2_correction.py prepare
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r378_gate_b2_correction.py execute \
        --expected-seal-sha256 <sha256>

The R377 execution is immutable and read-only input.  R378 changes exactly
one rule (settling improvement: at least one dt below local -> no worse than
local), reanalyses the 60 immutable development records, and executes the
30-record held-out bank only if a candidate is selected.  No training, retry,
gain change, bank resize, or parallel execution.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
for path in (ROOT, SCRIPT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

for thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[thread_variable] = "1"
os.environ["DISABLE_TOGGLER"] = "1"

from run_r372_energy_port_object_gate import (  # noqa: E402
    _canonical_bytes,
    _installed_runtime,
    _memory_resources,
    _read_hashed_json,
    _relative,
    _sha256_file,
    _write_new_json,
)
from run_r377_gate_b2_deterministic import _run_job  # noqa: E402

from andes_rl_kundur.evaluation.gate_b2_correction import (  # noqa: E402
    build_corrected_contract,
    classify_summaries,
    summarize_immutable_development,
    validate_correction,
)
from andes_rl_kundur.evaluation.gate_b2_deterministic import (  # noqa: E402
    build_contract,
    phase_jobs,
    summarize_phase_records,
)

ROUND_ID = "R378"
ROUND_DIR = ROOT / "memory/rounds/R378"
PLAN = ROUND_DIR / "plan.md"
REHEARSAL = ROUND_DIR / "rehearsal.json"
CAPACITY = ROUND_DIR / "capacity_evidence.json"
SEAL = ROUND_DIR / "formal_seal.json"
DEFAULT_OUT = ROOT / "results/research_loop/r378_gate_b2_correction"
R377_DIR = ROOT / "results/research_loop/r377_gate_b2_deterministic"
R377_DEVELOPMENT = R377_DIR / "development_execution.json"
R377_PLAN = ROOT / "memory/rounds/R377/plan.md"
R377_SEAL = ROOT / "memory/rounds/R377/formal_seal.json"


def _other_research_python_processes() -> list[dict[str, Any]]:
    """Detect competing research Python processes, ignoring shell wrappers."""
    if os.name != "posix":
        return []
    own_pid = os.getpid()
    matches: list[dict[str, Any]] = []
    for path in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            pid = int(path.parent.name)
            if pid == own_pid:
                continue
            command = path.read_bytes().replace(b"\x00", b" ").decode(
                "utf-8", errors="replace"
            )
        except (OSError, ValueError):
            continue
        lowered = command.lower()
        if "python" not in lowered:
            continue
        try:
            executable = str(Path(f"/proc/{pid}/exe").readlink()).lower()
        except OSError:
            continue
        if "python" not in executable:
            continue
        if "andes-rl-kundur" in lowered and (
            "run_r" in lowered or "train" in lowered or "eval" in lowered
        ):
            matches.append({"pid": pid, "command": command.strip()})
    return matches


def _payload_sha256(payload: object) -> str:
    import hashlib

    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _source_paths() -> dict[str, Path]:
    return {
        "plan": PLAN,
        "line": ROOT / "paper/paralleled_vsg_marl/LINE.md",
        "route": ROOT / "paper/paralleled_vsg_marl/ROUTE.md",
        "gate_b2_contract": (
            ROOT
            / "paper/paralleled_vsg_marl/working/"
            "gate_b2_deterministic_physical_contract.md"
        ),
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_r378_gate_b2_correction.py",
        "correction": (
            ROOT / "src/andes_rl_kundur/evaluation/gate_b2_correction.py"
        ),
        "correction_tests": ROOT / "tests/test_gate_b2_correction.py",
        "r377_runner": ROOT / "scripts/run_r377_gate_b2_deterministic.py",
        "r377_classifier": (
            ROOT / "src/andes_rl_kundur/evaluation/gate_b2_deterministic.py"
        ),
        "r372_runner_infrastructure": (
            ROOT / "scripts/run_r372_energy_port_object_gate.py"
        ),
        "controller": (
            ROOT
            / "src/andes_rl_kundur/control/"
            "feasibility_native_deterministic.py"
        ),
        "action_map": (
            ROOT
            / "src/andes_rl_kundur/control/feasibility_native_vsg_action.py"
        ),
        "energy_contract": ROOT / "src/andes_rl_kundur/control/active_power.py",
        "energy_port": ROOT / "src/andes_rl_kundur/control/vsg_energy_port.py",
        "energy_port_environment": (
            ROOT / "src/andes_rl_kundur/env/andes/vsg_energy_port_env.py"
        ),
        "base_environment": ROOT / "src/andes_rl_kundur/env/andes/base_env.py",
        "v4_environment": (
            ROOT / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py"
        ),
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "dependencies": ROOT / "pyproject.toml",
    }


def _source_manifest() -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for name, path in _source_paths().items():
        if not path.is_file():
            raise FileNotFoundError(f"missing R378 source: {path}")
        result[name] = {"path": _relative(path), "sha256": _sha256_file(path)}
    return result


def _parent_paths() -> dict[str, Path]:
    return {
        "r377_plan": R377_PLAN,
        "r377_seal": R377_SEAL,
        "r377_development_execution": R377_DEVELOPMENT,
        "r377_development_sidecar": Path(f"{R377_DEVELOPMENT}.sha256"),
        "r377_analysis": R377_DIR / "formal_analysis.json",
        "r377_development_analysis": R377_DIR / "development_analysis.json",
        "r377_attempt": R377_DIR / "formal_attempt.json",
        "r377_feed": ROOT / "paper/paralleled_vsg_marl/reports/R377.md",
        "r377_verdict": ROOT / "memory/rounds/R377/verdict.md",
        "r377_claim": ROOT / "memory/claims/CLM-1030.md",
    }


def _parent_manifest() -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for name, path in _parent_paths().items():
        if not path.is_file():
            raise FileNotFoundError(f"missing R378 parent: {path}")
        result[name] = {"path": _relative(path), "sha256": _sha256_file(path)}
    return result


def _sidecar_matches(path: Path) -> bool:
    sidecar = Path(f"{path}.sha256")
    if not sidecar.is_file():
        return False
    fields = sidecar.read_text(encoding="utf-8").strip().split()
    return bool(
        len(fields) == 2
        and fields[0] == _sha256_file(path)
        and fields[1] == path.name
    )


def _plan_is_active() -> bool:
    text = PLAN.read_text(encoding="utf-8")
    return "round: R378" in text and "state: active" in text


def _contract_is_closed(contract: Mapping[str, Any]) -> bool:
    try:
        return bool(
            contract["round"] == ROUND_ID
            and contract.get("correction_scope") == ["round", "settling_rule"]
            and int(contract["steps"]) == 50
            and float(contract["dt_seconds"]) == 0.2
            and int(contract["development"]["record_count"]) == 60
            and int(contract["evaluation"]["record_count"]) == 30
            and len(contract["distributed_candidates"]) == 4
            and contract["training_authorized"] is False
        )
    except (KeyError, TypeError, ValueError):
        return False


def _projected_artifact_bytes(contract: Mapping[str, Any]) -> int:
    return max(20_000_000, 2 * R377_DEVELOPMENT.stat().st_size)


def _build_capacity_payload(
    *,
    anchor_wall_seconds: float,
    projected_artifact_bytes: int,
    disk_free_bytes: int,
    logical_processors: int,
    physical_memory_bytes: int,
    wsl_memory_available_bytes: int,
    runtime: Mapping[str, Any],
    sources: Mapping[str, Any],
    parents: Mapping[str, Any],
) -> dict[str, Any]:
    point_wall = anchor_wall_seconds * 30.0 / 60.0
    guarded_wall = 1.5 * point_wall
    checks = {
        "anchor_complete": anchor_wall_seconds > 0.0,
        "runtime_ready": (
            runtime.get("andes_version") == "2.0.0"
            and bool(runtime.get("case_sha256"))
        ),
        "host_observed": logical_processors > 0 and physical_memory_bytes > 0,
        "memory_fit": wsl_memory_available_bytes > 1_000_000_000,
        "artifact_fit": disk_free_bytes > 100 * projected_artifact_bytes,
        "source_hashes_present": all(
            bool(row.get("sha256")) for row in sources.values()
        ),
        "parent_hashes_present": all(
            bool(row.get("sha256")) for row in parents.values()
        ),
    }
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "readiness": "RUN-READY" if all(checks.values()) else "HOLD",
        "checks": checks,
        "empirical_anchor": {
            "round": "R377",
            "record_count": 60,
            "environment_steps": 3000,
            "wall_seconds": anchor_wall_seconds,
            "concurrent_workers": 1,
            "native_threads_per_worker": 1,
        },
        "reused_development": {
            "record_count": 60,
            "environment_steps": 3000,
            "new_physical_execution": False,
        },
        "maximum_new_execution": {
            "phase": "conditional_held_out",
            "record_count": 30,
            "environment_steps": 1500,
            "point_estimate_wall_seconds": point_wall,
            "wall_seconds_with_1p5_safety_factor": guarded_wall,
        },
        "artifact_projection": {
            "projected_bytes": projected_artifact_bytes,
            "disk_free_bytes": disk_free_bytes,
        },
        "host": {
            "logical_processors": logical_processors,
            "physical_memory_bytes": physical_memory_bytes,
        },
        "wsl": {"memory_available_bytes": wsl_memory_available_bytes},
        "installed_runtime": dict(runtime),
        "whole_host_python_process_budget": 1,
        "host_process_budget": 1,
        "wsl_python_processes": 1,
        "native_threads_per_process": 1,
        "other_reserved_processes": 0,
        "sources": dict(sources),
        "parents": dict(parents),
        "performance_fields_parsed": False,
        "formal_authority": False,
        "training_executed": False,
    }


def _rehearsal_checks(payload: Mapping[str, Any]) -> bool:
    checks = dict(payload.get("checks", {}))
    expected = {
        "source_hash",
        "parent_hash",
        "parent_sidecars",
        "installed_package",
        "installed_case",
        "output_absence",
        "active_plan",
        "contract_single_diff",
        "correction_valid",
        "capacity_ready",
        "competing_process_absence",
        "artifact_fit",
        "performance_fields_parsed",
        "physical_trajectory_executed",
    }
    false_checks = {"performance_fields_parsed", "physical_trajectory_executed"}
    return bool(
        set(checks) == expected
        and all(bool(value) for name, value in checks.items() if name not in false_checks)
        and all(checks[name] is False for name in false_checks)
    )


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("R378 physical/rehearsal commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R378 must run through scripts/andes_scratch.py")


def rehearse() -> tuple[str, str]:
    _assert_wsl_scratch()
    collisions = [
        path for path in (REHEARSAL, CAPACITY, SEAL, DEFAULT_OUT) if path.exists()
    ]
    if collisions:
        raise FileExistsError(f"R378 readiness output collision: {collisions}")
    sources = _source_manifest()
    parents = _parent_manifest()
    contract = build_corrected_contract(build_contract())
    correction_valid = validate_correction(build_contract(), contract)
    runtime = _installed_runtime()
    other = _other_research_python_processes()
    logical, physical, wsl_available = _memory_resources()
    disk_free = shutil.disk_usage(ROOT).free
    r377_analysis = _read_hashed_json(_parent_paths()["r377_analysis"])
    anchor_wall = float(r377_analysis["wall_seconds"])
    projected_bytes = _projected_artifact_bytes(contract)
    capacity = _build_capacity_payload(
        anchor_wall_seconds=anchor_wall,
        projected_artifact_bytes=projected_bytes,
        disk_free_bytes=disk_free,
        logical_processors=logical,
        physical_memory_bytes=physical,
        wsl_memory_available_bytes=wsl_available,
        runtime=runtime,
        sources=sources,
        parents=parents,
    )
    capacity["other_processes"] = other
    capacity["checks"]["competing_process_absence"] = not other
    if other:
        capacity["readiness"] = "HOLD"
    capacity_sha = _write_new_json(CAPACITY, capacity)
    checks = {
        "source_hash": all(item["sha256"] for item in sources.values()),
        "parent_hash": all(item["sha256"] for item in parents.values()),
        "parent_sidecars": all(
            _sidecar_matches(path)
            for path in (
                R377_SEAL,
                R377_DEVELOPMENT,
                R377_DIR / "development_analysis.json",
                R377_DIR / "formal_attempt.json",
            )
        ),
        "installed_package": runtime.get("andes_version") == "2.0.0",
        "installed_case": bool(runtime.get("case_sha256")),
        "output_absence": not DEFAULT_OUT.exists() and not SEAL.exists(),
        "active_plan": _plan_is_active(),
        "contract_single_diff": _contract_is_closed(contract),
        "correction_valid": correction_valid,
        "capacity_ready": capacity["readiness"] == "RUN-READY",
        "competing_process_absence": not other,
        "artifact_fit": bool(capacity["checks"]["artifact_fit"]),
        "performance_fields_parsed": False,
        "physical_trajectory_executed": False,
    }
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "checks": checks,
        "readiness": (
            "RUN-READY" if _rehearsal_checks({"checks": checks}) else "HOLD"
        ),
        "contract_sha256": _payload_sha256(contract),
        "capacity_sha256": capacity_sha,
        "sources": sources,
        "parents": parents,
        "installed_runtime": runtime,
        "formal_authority": False,
        "training_executed": False,
    }
    rehearsal_sha = _write_new_json(REHEARSAL, payload)
    if payload["readiness"] != "RUN-READY":
        raise RuntimeError(f"R378 rehearsal HOLD: {checks}")
    print(f"readiness=RUN-READY rehearsal_sha256={rehearsal_sha}", flush=True)
    return rehearsal_sha, capacity_sha


def prepare() -> str:
    if SEAL.exists() or DEFAULT_OUT.exists():
        raise FileExistsError("R378 seal or formal output already exists")
    rehearsal = _read_hashed_json(REHEARSAL)
    capacity = _read_hashed_json(CAPACITY)
    if rehearsal.get("readiness") != "RUN-READY" or not _rehearsal_checks(rehearsal):
        raise RuntimeError("R378 rehearsal is not RUN-READY")
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R378 capacity is not RUN-READY")
    sources = _source_manifest()
    parents = _parent_manifest()
    if sources != rehearsal["sources"] or parents != rehearsal["parents"]:
        raise RuntimeError("R378 source or parent drift after rehearsal")
    contract = build_corrected_contract(build_contract())
    if _payload_sha256(contract) != rehearsal["contract_sha256"]:
        raise RuntimeError("R378 contract drift after rehearsal")
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_sha256": _payload_sha256(contract),
        "correction_scope": ["round", "settling_rule"],
        "sources": sources,
        "parents": parents,
        "installed_runtime": rehearsal["installed_runtime"],
        "capacity_sha256": _sha256_file(CAPACITY),
        "rehearsal_sha256": _sha256_file(REHEARSAL),
        "launch": {
            "host_process_budget": 1,
            "wsl_python_processes": 1,
            "native_threads_per_process": 1,
            "other_reserved_processes": 0,
        },
        "parent_performance_fields_parsed_before_seal": False,
        "conditional_held_out_only": True,
        "formal_artifacts_create_only": True,
        "retry_authorized": False,
        "training_authorized": False,
    }
    digest = _write_new_json(SEAL, payload)
    print(f"seal_sha256={digest}", flush=True)
    return digest


def _load_seal(expected_sha256: str) -> tuple[dict[str, Any], str]:
    seal = _read_hashed_json(SEAL)
    digest = _sha256_file(SEAL)
    if digest != expected_sha256:
        raise RuntimeError("R378 expected seal hash does not match")
    if seal.get("contract_sha256") != _payload_sha256(seal["contract"]):
        raise RuntimeError("R378 sealed contract hash mismatch")
    if seal.get("sources") != _source_manifest():
        raise RuntimeError("R378 source drift after seal")
    if seal.get("parents") != _parent_manifest():
        raise RuntimeError("R378 parent drift after seal")
    if seal.get("rehearsal_sha256") != _sha256_file(REHEARSAL):
        raise RuntimeError("R378 rehearsal drift after seal")
    if seal.get("capacity_sha256") != _sha256_file(CAPACITY):
        raise RuntimeError("R378 capacity drift after seal")
    if not _contract_is_closed(seal["contract"]):
        raise RuntimeError("R378 corrected contract is not closed")
    return seal, digest


def _manifest_entry(path: Path, digest: str) -> dict[str, str]:
    return {"path": _relative(path), "sha256": digest}


def execute(*, expected_sha256: str) -> str:
    _assert_wsl_scratch()
    seal, seal_digest = _load_seal(expected_sha256)
    other = _other_research_python_processes()
    if other:
        raise RuntimeError(f"other research Python processes are active: {other}")
    if DEFAULT_OUT.exists():
        raise FileExistsError(f"R378 output collision: {DEFAULT_OUT}")
    attempt_path = DEFAULT_OUT / "formal_attempt.json"
    attempt_digest = _write_new_json(
        attempt_path,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "seal_sha256": seal_digest,
            "retry_authorized": False,
            "training_authorized": False,
        },
    )
    started = time.perf_counter()
    entries = [_manifest_entry(attempt_path, attempt_digest)]
    try:
        contract = seal["contract"]
        development_execution = _read_hashed_json(R377_DEVELOPMENT)
        if int(development_execution.get("record_count", -1)) != 60:
            raise RuntimeError("R377 development record count drift")
        development_records = list(development_execution.get("records", ()))
        immutable = summarize_immutable_development(
            development_records,
            contract=contract,
        )
        selection = immutable["selection"]
        development_analysis_path = DEFAULT_OUT / "development_analysis.json"
        development_analysis_digest = _write_new_json(
            development_analysis_path,
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "seal_sha256": seal_digest,
                "parent_development_execution_sha256": _sha256_file(
                    R377_DEVELOPMENT
                ),
                "development": immutable["development"],
                "selection": selection,
                "held_out_inspected": False,
                "training_authorized": False,
            },
        )
        entries.append(
            _manifest_entry(development_analysis_path, development_analysis_digest)
        )

        selected = selection.get("selected_arm_id")
        evaluation_phase: dict[str, Any] | None = None
        held_out_executed = False
        if selection["classification"] == "DEVELOPMENT-CANDIDATE-SELECTED":
            evaluation_records = [
                _run_job(job, contract=contract)
                for job in phase_jobs(
                    "evaluation",
                    selected_arm_id=str(selected),
                    contract=contract,
                )
            ]
            held_out_executed = True
            evaluation_execution_path = DEFAULT_OUT / "evaluation_execution.json"
            evaluation_execution_digest = _write_new_json(
                evaluation_execution_path,
                {
                    "schema_version": 1,
                    "round": ROUND_ID,
                    "seal_sha256": seal_digest,
                    "development_selection_sha256": development_analysis_digest,
                    "record_count": len(evaluation_records),
                    "records": evaluation_records,
                    "reward_used_for_gate": False,
                    "training_executed": False,
                },
            )
            entries.append(
                _manifest_entry(
                    evaluation_execution_path,
                    evaluation_execution_digest,
                )
            )
            evaluation_phase = summarize_phase_records(
                evaluation_records,
                phase="evaluation",
                selected_arm_id=str(selected),
                contract=contract,
            )
            analysis = classify_summaries(
                selection,
                evaluation_phase["arm_summaries"],
                contract=contract,
            )
        else:
            analysis = {
                "classification": selection["classification"],
                "checks": {"development_candidate": False},
                "selected_arm_id": None,
                "training_authorized": False,
                "next_gate": None,
            }
        analysis.update(
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "seal_sha256": seal_digest,
                "parent_development_execution_sha256": _sha256_file(
                    R377_DEVELOPMENT
                ),
                "development_analysis_sha256": development_analysis_digest,
                "development_selection": selection,
                "evaluation": evaluation_phase,
                "held_out_executed": held_out_executed,
                "wall_seconds": time.perf_counter() - started,
                "performance_fields_parsed_after_seal": True,
                "training_authorized": False,
            }
        )
        analysis_path = DEFAULT_OUT / "formal_analysis.json"
        analysis_digest = _write_new_json(analysis_path, analysis)
        entries.append(_manifest_entry(analysis_path, analysis_digest))
        _write_new_json(
            DEFAULT_OUT / "formal_manifest.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "entries": entries,
            },
        )
        print(f"classification={analysis['classification']}", flush=True)
        return analysis_digest
    except Exception as exc:
        _write_new_json(
            DEFAULT_OUT / "formal_failure.json",
            {
                "schema_version": 1,
                "round": ROUND_ID,
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
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("rehearse")
    subparsers.add_parser("prepare")
    execute_parser = subparsers.add_parser("execute")
    execute_parser.add_argument("--expected-seal-sha256", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "rehearse":
        rehearse()
    elif args.command == "prepare":
        prepare()
    else:
        execute(expected_sha256=args.expected_seal_sha256)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
