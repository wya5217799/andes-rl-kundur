#!/usr/bin/env python3
"""Rehearse, seal, and execute the create-only R381 Gate B-4 bank.

Usage (WSL)::

    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r381_gate_b4_deterministic.py rehearse
    /home/wya/andes_venv/bin/python scripts/run_r381_gate_b4_deterministic.py prepare
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r381_gate_b4_deterministic.py execute \
        --expected-seal-sha256 <sha256>

R381 reuses the immutable R379 execution machinery and endpoint classifier,
but replaces the stopped first-order candidate grid with one prospectively
fixed second-order washout controller.  There is no training, retry, tuning,
parallel worker, or outcome-dependent bank command.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
for import_path in (ROOT, SCRIPT_DIR, ROOT / "src"):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

for thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[thread_variable] = "1"
os.environ["DISABLE_TOGGLER"] = "1"

import run_r379_gate_b3_deterministic as _base  # noqa: E402

from andes_rl_kundur.control.cascaded_washout import (  # noqa: E402
    CascadedHPDampingDistributedController,
)
from andes_rl_kundur.control.feasibility_native_deterministic import (  # noqa: E402
    FeasibilityNativeLocalController,
)
from andes_rl_kundur.evaluation.gate_b4_deterministic import (  # noqa: E402
    CANDIDATE_ARM,
    build_contract,
    classify_summaries,
    controller_spec,
    phase_jobs,
    probe_request,
    select_development_candidate,
    summarize_phase_records,
)


ROUND_ID = "R381"
ROUND_DIR = ROOT / "memory/rounds/R381"
PLAN = ROUND_DIR / "plan.md"
REHEARSAL = ROUND_DIR / "rehearsal.json"
CAPACITY = ROUND_DIR / "capacity_evidence.json"
SEAL = ROUND_DIR / "formal_seal.json"
DEFAULT_OUT = ROOT / "results/research_loop/r381_gate_b4_deterministic"


def _source_paths() -> dict[str, Path]:
    return {
        "plan": PLAN,
        "line": ROOT / "paper/paralleled_vsg_marl/LINE.md",
        "route": ROOT / "paper/paralleled_vsg_marl/ROUTE.md",
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_r381_gate_b4_deterministic.py",
        "runner_infrastructure": (
            ROOT / "scripts/run_r379_gate_b3_deterministic.py"
        ),
        "controller": (
            ROOT / "src/andes_rl_kundur/control/cascaded_washout.py"
        ),
        "controller_tests": (
            ROOT / "tests/test_cascaded_hp_damping_controller.py"
        ),
        "classifier": (
            ROOT / "src/andes_rl_kundur/evaluation/gate_b4_deterministic.py"
        ),
        "classifier_tests": ROOT / "tests/test_gate_b4_deterministic.py",
        "classifier_infrastructure": (
            ROOT / "src/andes_rl_kundur/evaluation/gate_b3_deterministic.py"
        ),
        "local_controller": (
            ROOT
            / "src/andes_rl_kundur/control/feasibility_native_deterministic.py"
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


def _parent_paths() -> dict[str, Path]:
    root = ROOT / "results/research_loop/r377_gate_b3_deterministic"
    return {
        "r379_seal": ROOT / "memory/rounds/R379/formal_seal.json",
        "r379_capacity": ROOT / "memory/rounds/R379/capacity_evidence.json",
        "r379_development": root / "development_execution.json",
        "r379_development_analysis": root / "development_analysis.json",
        "r379_analysis": root / "formal_analysis.json",
        "r379_feed": ROOT / "paper/paralleled_vsg_marl/reports/R379.md",
        "r379_verdict": ROOT / "memory/rounds/R379/verdict.md",
        "r379_claim": ROOT / "memory/claims/CLM-1040.md",
    }


def _plan_is_active() -> bool:
    text = PLAN.read_text(encoding="utf-8")
    return "round: R381" in text and "state: active" in text


def _contract_is_closed(contract: Mapping[str, Any]) -> bool:
    try:
        candidate = contract["distributed_candidates"]
        return bool(
            contract["round"] == ROUND_ID
            and int(contract["steps"]) == 50
            and float(contract["dt_seconds"]) == 0.2
            and float(contract["probe_component_action"]) == 0.25
            and float(contract["controller_action_clip"]) == 0.70
            and float(contract["highpass_alpha"]) == 0.9391013674242926
            and int(contract["filter_order"]) == 2
            and float(contract["corner_hz"]) == 0.05
            and int(contract["development"]["record_count"]) == 30
            and int(contract["evaluation"]["record_count"]) == 30
            and len(candidate) == 1
            and candidate[0]["arm_id"] == CANDIDATE_ARM
            and len(phase_jobs("development", contract=contract)) == 30
            and contract["training_authorized"] is False
        )
    except (KeyError, TypeError, ValueError):
        return False


def _make_controller(
    arm_id: str,
    contract: Mapping[str, Any],
) -> Any | None:
    spec = controller_spec(arm_id, contract=contract)
    architecture = spec["architecture"]
    common = {
        "device_count": int(contract["device_count"]),
        "nominal_frequency_hz": float(contract["nominal_frequency_hz"]),
        "kp_n_per_hz": float(spec.get("kp_n_per_hz", 0.0)),
        "ki_n_per_hz_s": float(spec.get("ki_n_per_hz_s", 0.0)),
    }
    if architecture == "zero_feedback":
        return None
    if architecture == "local_feasibility_native":
        return FeasibilityNativeLocalController(**common)
    if architecture != "distributed_cascaded_hp_damping":
        raise ValueError(f"unknown R381 architecture: {architecture}")
    adjacency = {
        int(index): tuple(neighbours)
        for index, neighbours in contract["adjacency"].items()
    }
    return CascadedHPDampingDistributedController(
        adjacency=adjacency,
        **common,
        ks_n_per_hz=float(spec["sync_gain_per_hz"]),
        kc_n_per_s=float(spec["consensus_gain_per_s"]),
        highpass_alpha=float(spec["highpass_alpha"]),
    )


def _configure_base() -> None:
    """Bind immutable R379 machinery to the R381 identity and mechanism."""
    _base.ROUND_ID = ROUND_ID
    _base.ROUND_DIR = ROUND_DIR
    _base.PLAN = PLAN
    _base.REHEARSAL = REHEARSAL
    _base.CAPACITY = CAPACITY
    _base.SEAL = SEAL
    _base.DEFAULT_OUT = DEFAULT_OUT
    _base.build_contract = build_contract
    _base.controller_spec = controller_spec
    _base.phase_jobs = phase_jobs
    _base.probe_request = probe_request
    _base.select_development_candidate = select_development_candidate
    _base.summarize_phase_records = summarize_phase_records
    _base.classify_summaries = classify_summaries
    _base._source_paths = _source_paths
    _base._parent_paths = _parent_paths
    _base._plan_is_active = _plan_is_active
    _base._contract_is_closed = _contract_is_closed
    _base._make_controller = _make_controller


def _capacity_payload(
    *,
    projected_artifact_bytes: int,
    disk_free_bytes: int,
    logical_processors: int,
    physical_memory_bytes: int,
    wsl_memory_available_bytes: int,
    runtime: Mapping[str, Any],
    sources: Mapping[str, Any],
    parents: Mapping[str, Any],
) -> dict[str, Any]:
    anchor_capacity = _base._read_hashed_json(_parent_paths()["r379_capacity"])
    anchor_analysis = _base._read_hashed_json(_parent_paths()["r379_analysis"])
    compatibility_parents = {
        "r374_development": parents["r379_development"],
        "r375_capacity": parents["r379_capacity"],
    }
    payload = _base._build_capacity_payload(
        anchor_execution={
            "record_count": 60,
            "wall_seconds": float(anchor_analysis["wall_seconds"]),
        },
        anchor_capacity=anchor_capacity,
        projected_artifact_bytes=projected_artifact_bytes,
        disk_free_bytes=disk_free_bytes,
        logical_processors=logical_processors,
        physical_memory_bytes=physical_memory_bytes,
        wsl_memory_available_bytes=wsl_memory_available_bytes,
        runtime=runtime,
        sources=sources,
        parents=compatibility_parents,
    )
    payload["parents"] = dict(parents)
    payload["empirical_anchor"].update(
        {
            "execution_path": parents["r379_development"]["path"],
            "execution_sha256": parents["r379_development"]["sha256"],
            "capacity_path": parents["r379_capacity"]["path"],
            "capacity_sha256": parents["r379_capacity"]["sha256"],
            "analysis_path": parents["r379_analysis"]["path"],
            "analysis_sha256": parents["r379_analysis"]["sha256"],
        }
    )
    payload["host_process_budget_classification"] = (
        "intentional_attempt_level_hard_cap"
    )
    return payload


def rehearse() -> tuple[str, str]:
    _configure_base()
    _base._assert_wsl_scratch()
    collisions = [
        path for path in (REHEARSAL, CAPACITY, SEAL, DEFAULT_OUT) if path.exists()
    ]
    if collisions:
        raise FileExistsError(f"R381 readiness output collision: {collisions}")

    contract = build_contract()
    sources = _base._source_manifest()
    parents = _base._parent_manifest()
    runtime = _base._installed_runtime()
    other = _base._other_research_python_processes()
    logical, physical, wsl_available = _base._memory_resources()
    projected_bytes = _base._projected_artifact_bytes(contract)
    capacity = _capacity_payload(
        projected_artifact_bytes=projected_bytes,
        disk_free_bytes=shutil.disk_usage(ROOT).free,
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
    capacity_sha = _base._write_new_json(CAPACITY, capacity)

    hashed_parents = (
        _parent_paths()["r379_seal"],
        _parent_paths()["r379_capacity"],
        _parent_paths()["r379_development"],
        _parent_paths()["r379_development_analysis"],
        _parent_paths()["r379_analysis"],
    )
    checks = {
        "source_hash": all(item["sha256"] for item in sources.values()),
        "parent_hash": all(item["sha256"] for item in parents.values()),
        "parent_sidecars": all(_base._sidecar_matches(path) for path in hashed_parents),
        "installed_package": runtime.get("andes_version") == "2.0.0",
        "installed_case": bool(runtime.get("case_sha256")),
        "output_absence": not DEFAULT_OUT.exists() and not SEAL.exists(),
        "active_plan": _plan_is_active(),
        "contract_closed": _contract_is_closed(contract),
        "capacity_ready": capacity["readiness"] == "RUN-READY",
        "competing_process_absence": not other,
        "artifact_fit": bool(capacity["checks"]["artifact_fit"]),
        "physical_trajectory_executed": False,
    }
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "checks": checks,
        "readiness": (
            "RUN-READY"
            if _base._rehearsal_checks({"checks": checks})
            else "HOLD"
        ),
        "contract_sha256": _base._payload_sha256(contract),
        "capacity_sha256": capacity_sha,
        "sources": sources,
        "parents": parents,
        "installed_runtime": runtime,
        "formal_authority": False,
        "training_executed": False,
    }
    rehearsal_sha = _base._write_new_json(REHEARSAL, payload)
    if payload["readiness"] != "RUN-READY":
        raise RuntimeError(f"R381 rehearsal HOLD: {checks}")
    print(
        f"readiness=RUN-READY rehearsal_sha256={rehearsal_sha}",
        flush=True,
    )
    return rehearsal_sha, capacity_sha


def prepare() -> str:
    _configure_base()
    return _base.prepare()


def execute(*, expected_sha256: str) -> str:
    _configure_base()
    return _base.execute(expected_sha256=expected_sha256)


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
