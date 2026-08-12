#!/usr/bin/env python3
"""Rehearse, seal, and execute the create-only R376 Gate B deterministic bank.

Usage (WSL):
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r376_gate_b_deterministic.py rehearse
    /home/wya/andes_venv/bin/python scripts/run_r376_gate_b_deterministic.py prepare
    /home/wya/andes_venv/bin/python scripts/andes_scratch.py \
        scripts/run_r376_gate_b_deterministic.py execute \
        --expected-seal-sha256 <sha256>

The adapter contains no training, retry, gain override, bank resize, or
parallel-execution command.  Formal artifacts are create-only.  Every arm maps
one scalar normalized action per VSG through the feasibility-native map; the
outer VSG energy-port projection must be identity on every step.
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

import numpy as np

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
    _identity,
    _installed_runtime,
    _memory_resources,
    _port_row,
    _read_hashed_json,
    _relative,
    _sha256_file,
    _write_new_json,
)

from andes_rl_kundur.control.active_power import (  # noqa: E402
    r272_frozen_bess_contract,
)
from andes_rl_kundur.control.feasibility_native_deterministic import (  # noqa: E402
    FeasibilityNativeDistributedController,
    FeasibilityNativeLocalController,
)
from andes_rl_kundur.control.feasibility_native_vsg_action import (  # noqa: E402
    FeasibilityNativeVSGActionMap,
)
from andes_rl_kundur.evaluation.gate_b_deterministic import (  # noqa: E402
    build_contract,
    classify_summaries,
    controller_spec,
    phase_jobs,
    probe_request,
    select_development_candidate,
    summarize_phase_records,
)

ROUND_ID = "R376"
ROUND_DIR = ROOT / "memory/rounds/R376"
PLAN = ROUND_DIR / "plan.md"
REHEARSAL = ROUND_DIR / "rehearsal.json"


def _other_research_python_processes() -> list[dict[str, Any]]:
    """Detect competing research Python processes, ignoring shell wrappers.

    The R372 helper flags any command line containing ``python`` plus a
    ``run_r`` token, which also matches the ``bash -lc`` wrapper that
    launches this runner.  This R376-local detector therefore requires the
    process executable itself to be a Python interpreter.
    """
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
CAPACITY = ROUND_DIR / "capacity_evidence.json"
SEAL = ROUND_DIR / "formal_seal.json"
DEFAULT_OUT = ROOT / "results/research_loop/r376_gate_b_deterministic"


def _payload_sha256(payload: object) -> str:
    import hashlib

    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _source_paths() -> dict[str, Path]:
    return {
        "plan": PLAN,
        "line": ROOT / "paper/paralleled_vsg_marl/LINE.md",
        "route": ROOT / "paper/paralleled_vsg_marl/ROUTE.md",
        "gate_a_contract": (
            ROOT
            / "paper/paralleled_vsg_marl/working/"
            "feasibility_native_four_vsg_contract.md"
        ),
        "gate_b_contract": (
            ROOT
            / "paper/paralleled_vsg_marl/working/"
            "gate_b_deterministic_physical_contract.md"
        ),
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_r376_gate_b_deterministic.py",
        "controller": (
            ROOT
            / "src/andes_rl_kundur/control/"
            "feasibility_native_deterministic.py"
        ),
        "controller_tests": (
            ROOT
            / "tests/test_feasibility_native_deterministic.py"
        ),
        "action_map": (
            ROOT
            / "src/andes_rl_kundur/control/feasibility_native_vsg_action.py"
        ),
        "action_map_tests": ROOT / "tests/test_feasibility_native_vsg_action.py",
        "classifier": (
            ROOT / "src/andes_rl_kundur/evaluation/gate_b_deterministic.py"
        ),
        "classifier_tests": (
            ROOT / "tests/test_gate_b_deterministic.py"
        ),
        "r372_runner_infrastructure": (
            ROOT / "scripts/run_r372_energy_port_object_gate.py"
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
            raise FileNotFoundError(f"missing R376 source: {path}")
        result[name] = {"path": _relative(path), "sha256": _sha256_file(path)}
    return result


def _parent_paths() -> dict[str, Path]:
    return {
        "r375_seal": ROOT / "memory/rounds/R375/formal_seal.json",
        "r375_capacity": ROOT / "memory/rounds/R375/capacity_evidence.json",
        "r375_analysis": (
            ROOT
            / "results/research_loop/"
            "r375_deterministic_decoupling_identity_correction/"
            "formal_analysis.json"
        ),
        "r375_feed": ROOT / "paper/paralleled_vsg_marl/reports/R375.md",
        "r375_verdict": ROOT / "memory/rounds/R375/verdict.md",
        "r375_claim": ROOT / "memory/claims/CLM-1020.md",
        "r373_seal": ROOT / "memory/rounds/R373/formal_seal.json",
        "r373_authority_analysis": (
            ROOT
            / "results/research_loop/r373_energy_port_authority/"
            "formal_analysis.json"
        ),
        "r374_development": (
            ROOT
            / "results/research_loop/r374_deterministic_decoupling/"
            "development_execution.json"
        ),
    }


def _parent_manifest() -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for name, path in _parent_paths().items():
        if not path.is_file():
            raise FileNotFoundError(f"missing R376 parent: {path}")
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
    return "round: R376" in text and "state: active" in text


def _contract_is_closed(contract: Mapping[str, Any]) -> bool:
    try:
        return bool(
            contract["round"] == ROUND_ID
            and int(contract["steps"]) == 50
            and float(contract["dt_seconds"]) == 0.2
            and float(contract["probe_component_action"]) == 0.25
            and float(contract["controller_action_clip"]) == 0.70
            and int(contract["development"]["record_count"]) == 60
            and int(contract["evaluation"]["record_count"]) == 30
            and len(contract["distributed_candidates"]) == 4
            and len(phase_jobs("development", contract=contract)) == 60
            and contract["training_authorized"] is False
        )
    except (KeyError, TypeError, ValueError):
        return False


def _projected_artifact_bytes(contract: Mapping[str, Any]) -> int:
    zero4 = [0.0] * 4
    row = {
        "step_index": 0,
        "time": 0.0,
        "freq_hz_physical": [60.0] * 4,
        "requested_power_system_pu": zero4,
        "commanded_power_system_pu": zero4,
        "achieved_power_system_pu": zero4,
        "normalized_action": zero4,
        "controller_action": zero4,
        "common_action": zero4,
        "differential_action": zero4,
        "lower_power_system_pu": zero4,
        "upper_power_system_pu": zero4,
        "zero_anchor_power_system_pu": zero4,
        "feasible_power_system_pu": zero4,
        "headroom_fraction": zero4,
        "bound_contact": [False] * 4,
        "soc": [0.5] * 4,
        "saturation_reasons": [[], [], [], []],
        "md_action_norm": [[0.0, 0.0]] * 4,
        "tds_failed": False,
    }
    record = {
        "phase": "development",
        "arm_id": "zero_feedback",
        "experiment_kind": "probe",
        "condition_id": "placeholder",
        "delta_u": {},
        "input_mode": "common",
        "sign": "positive",
        "identity": {},
        "steps": [row] * int(contract["steps"]),
        "completed_steps": int(contract["steps"]),
        "tds_failed": False,
        "failure": None,
    }
    placeholder = {
        "development_execution": {
            "records": [record] * int(contract["development"]["record_count"])
        },
        "evaluation_execution": {
            "records": [record] * int(contract["evaluation"]["record_count"])
        },
        "development_analysis": {},
        "formal_analysis": {},
        "formal_manifest": {},
        "formal_attempt": {},
    }
    return 2 * len(_canonical_bytes(placeholder))


def _build_capacity_payload(
    *,
    anchor_execution: Mapping[str, Any],
    anchor_capacity: Mapping[str, Any],
    projected_artifact_bytes: int,
    disk_free_bytes: int,
    logical_processors: int,
    physical_memory_bytes: int,
    wsl_memory_available_bytes: int,
    runtime: Mapping[str, Any],
    sources: Mapping[str, Any],
    parents: Mapping[str, Any],
) -> dict[str, Any]:
    anchor_steps = 60 * 50
    formal_records = int(build_contract()["development"]["record_count"]) + int(
        build_contract()["evaluation"]["record_count"]
    )
    formal_steps = formal_records * int(build_contract()["steps"])
    projected_wall = (
        1.5 * float(anchor_execution["wall_seconds"]) * formal_steps / anchor_steps
    )
    anchor_runtime = dict(anchor_capacity["installed_runtime"])
    host = dict(anchor_capacity["host"])
    runtime_fields = [
        field
        for field in ("andes_version", "case_sha256")
        if field in anchor_runtime
    ]
    empirical_anchor = dict(anchor_capacity.get("empirical_anchor", {}))
    if "max_rss_kib" in empirical_anchor:
        memory_fit = wsl_memory_available_bytes > (
            8 * int(empirical_anchor["max_rss_kib"]) * 1024
        )
    else:
        prior_available = int(
            anchor_capacity.get("wsl", {}).get("memory_available_bytes", 0)
        )
        memory_fit = (
            bool(anchor_capacity.get("checks", {}).get("memory_fit"))
            and prior_available > 0
            and wsl_memory_available_bytes >= 0.8 * prior_available
        )
    checks = {
        "anchor_complete": (
            int(anchor_execution.get("record_count", -1)) == 60
            and float(anchor_execution.get("wall_seconds", 0.0)) > 0.0
        ),
        "anchor_serial": (
            int(anchor_capacity.get("wsl_python_processes", -1)) == 1
            and int(anchor_capacity.get("native_threads_per_process", -1)) == 1
        ),
        "runtime_match": bool(runtime_fields)
        and all(runtime.get(field) == anchor_runtime.get(field) for field in runtime_fields),
        "current_host": (
            logical_processors == int(host["logical_processors"])
            and physical_memory_bytes == int(host["physical_memory_bytes"])
        ),
        "memory_fit": memory_fit,
        "artifact_fit": disk_free_bytes > 100 * projected_artifact_bytes,
    }
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "readiness": "RUN-READY" if all(checks.values()) else "HOLD",
        "checks": checks,
        "empirical_anchor": {
            "all_records_valid": True,
            "concurrent_workers": 1,
            "native_threads_per_worker": 1,
            "execution_path": parents["r374_development"]["path"],
            "execution_sha256": parents["r374_development"]["sha256"],
            "capacity_path": parents["r375_seal"]["path"],
            "capacity_sha256": parents["r375_seal"]["sha256"],
            "record_count": int(anchor_execution["record_count"]),
            "environment_steps": anchor_steps,
            "wall_seconds": float(anchor_execution["wall_seconds"]),
        },
        "formal_projection": {
            "record_count": formal_records,
            "environment_steps": formal_steps,
            "wall_seconds_with_1p5_safety_factor": projected_wall,
        },
        "artifact_projection": {
            "method": "two times complete placeholder formal schema",
            "projected_bytes": projected_artifact_bytes,
            "disk_free_bytes": disk_free_bytes,
        },
        "host": {
            "logical_processors": logical_processors,
            "physical_memory_bytes": physical_memory_bytes,
        },
        "wsl": {"memory_available_bytes": wsl_memory_available_bytes},
        "memory_fit_rule": {
            "anchor_guard_required": True,
            "minimum_current_to_anchor_available_ratio": 0.8,
        },
        "installed_runtime": dict(runtime),
        "whole_host_python_process_budget": 1,
        "host_process_budget": 1,
        "wsl_python_processes": 1,
        "native_threads_per_process": 1,
        "other_reserved_processes": 0,
        "sources": dict(sources),
        "parents": dict(parents),
        "scientific_classification_inspected": False,
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
        "contract_closed",
        "capacity_ready",
        "competing_process_absence",
        "artifact_fit",
        "physical_trajectory_executed",
    }
    return (
        set(checks) == expected
        and all(
            bool(value)
            for name, value in checks.items()
            if name != "physical_trajectory_executed"
        )
        and checks["physical_trajectory_executed"] is False
    )


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("R376 physical/rehearsal commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R376 must run through scripts/andes_scratch.py")


def rehearse() -> tuple[str, str]:
    _assert_wsl_scratch()
    collisions = [
        path for path in (REHEARSAL, CAPACITY, SEAL, DEFAULT_OUT) if path.exists()
    ]
    if collisions:
        raise FileExistsError(f"R376 readiness output collision: {collisions}")
    contract = build_contract()
    sources = _source_manifest()
    parents = _parent_manifest()
    runtime = _installed_runtime()
    other = _other_research_python_processes()
    logical, physical, wsl_available = _memory_resources()
    disk_free = shutil.disk_usage(ROOT).free
    anchor_capacity = _read_hashed_json(_parent_paths()["r375_capacity"])
    anchor_execution = {
        "record_count": int(
            anchor_capacity["empirical_anchor"]["record_count"]
        ),
        "environment_steps": int(
            anchor_capacity["empirical_anchor"]["environment_steps"]
        ),
        "wall_seconds": float(anchor_capacity["empirical_anchor"]["wall_seconds"]),
    }
    projected_bytes = _projected_artifact_bytes(contract)
    capacity = _build_capacity_payload(
        anchor_execution=anchor_execution,
        anchor_capacity=anchor_capacity,
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
                ROOT / "memory/rounds/R375/formal_seal.json",
                ROOT / "memory/rounds/R375/capacity_evidence.json",
                ROOT
                / "results/research_loop/"
                "r375_deterministic_decoupling_identity_correction/"
                "formal_analysis.json",
                ROOT
                / "results/research_loop/r374_deterministic_decoupling/"
                "development_execution.json",
            )
        ),
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
        raise RuntimeError(f"R376 rehearsal HOLD: {checks}")
    print(f"readiness=RUN-READY rehearsal_sha256={rehearsal_sha}", flush=True)
    return rehearsal_sha, capacity_sha


def prepare() -> str:
    if SEAL.exists() or DEFAULT_OUT.exists():
        raise FileExistsError("R376 seal or formal output already exists")
    rehearsal = _read_hashed_json(REHEARSAL)
    capacity = _read_hashed_json(CAPACITY)
    if rehearsal.get("readiness") != "RUN-READY" or not _rehearsal_checks(rehearsal):
        raise RuntimeError("R376 rehearsal is not RUN-READY")
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R376 capacity is not RUN-READY")
    sources = _source_manifest()
    parents = _parent_manifest()
    if sources != rehearsal["sources"] or parents != rehearsal["parents"]:
        raise RuntimeError("R376 source or parent drift after rehearsal")
    contract = build_contract()
    if _payload_sha256(contract) != rehearsal["contract_sha256"]:
        raise RuntimeError("R376 contract drift after rehearsal")
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_sha256": _payload_sha256(contract),
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
        "formal_artifacts_create_only": True,
        "retry_authorized": False,
        "training_authorized": False,
    }
    digest = _write_new_json(SEAL, payload)
    print(f"seal_sha256={digest}", flush=True)
    return digest


def _make_controller(arm_id: str, contract: Mapping[str, Any]) -> Any | None:
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
    adjacency = {
        int(index): tuple(neighbours)
        for index, neighbours in contract["adjacency"].items()
    }
    return FeasibilityNativeDistributedController(
        adjacency=adjacency,
        **common,
        ks_n_per_hz=float(spec["sync_gain_per_hz"]),
        kc_n_per_s=float(spec["consensus_gain_per_s"]),
    )


def _run_job(job: Mapping[str, Any], *, contract: Mapping[str, Any]) -> dict[str, Any]:
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.env.andes.vsg_energy_port_env import AndesVSGEnergyPortEnv

    base_env = AndesMultiVSGEnvV4(
        random_disturbance=False,
        comm_fail_prob=0.0,
        comm_delay_steps=0,
    )
    base_env.seed(int(contract["seed"]))
    base_env.STEPS_PER_EPISODE = int(contract["steps"])
    port_env = AndesVSGEnergyPortEnv(base_env=base_env)
    action_map = FeasibilityNativeVSGActionMap(r272_frozen_bess_contract())
    controller = _make_controller(str(job["arm_id"]), contract)
    rows: list[dict[str, Any]] = []
    identity: dict[str, Any] | None = None
    failure: str | None = None
    previous_power_system_pu = np.zeros(4, dtype=float)
    current_soc = np.full(4, float(contract["soc_initial"]), dtype=float)
    try:
        port_env.reset(delta_u=dict(job["delta_u"]))
        identity = _identity(base_env)
        for step_index in range(int(contract["steps"])):
            frequencies = (
                np.asarray(base_env._get_vsg_omega(), dtype=float)
                * float(contract["nominal_frequency_hz"])
            )
            controller_action = (
                np.zeros(4, dtype=float)
                if controller is None
                else controller.act(
                    frequencies_hz=frequencies,
                    dt_seconds=float(contract["dt_seconds"]),
                )
            )
            normalized = controller_action.copy()
            if job["experiment_kind"] == "probe":
                normalized = normalized + probe_request(
                    str(job["input_mode"]),
                    str(job["sign"]),
                    contract=contract,
                )
            common_action = np.mean(normalized) * np.ones(4, dtype=float)
            differential_action = normalized - common_action
            voltage_pu = np.asarray(
                [
                    base_env.ss.GENCLS.v.v[position]
                    for position in base_env._vsg_pos
                ],
                dtype=float,
            )
            mapped = action_map.map_action(
                normalized_actions=normalized,
                previous_power_system_pu=previous_power_system_pu,
                soc=current_soc,
                voltage_pu=voltage_pu,
                dt_seconds=float(contract["dt_seconds"]),
            )
            _observation, _reward, done, info = port_env.step(
                mapped.feasible_power_system_pu
            )
            row = _port_row(info, step_index=step_index, done=bool(done))
            lower = np.asarray(mapped.lower_power_system_pu, dtype=float)
            upper = np.asarray(mapped.upper_power_system_pu, dtype=float)
            zero_anchor = np.asarray(
                mapped.zero_anchor_power_system_pu, dtype=float
            )
            feasible = np.asarray(mapped.feasible_power_system_pu, dtype=float)
            headroom_fraction = np.where(
                feasible >= 0.0,
                np.divide(
                    np.abs(feasible - zero_anchor),
                    upper - zero_anchor,
                    out=np.zeros_like(feasible),
                    where=(upper - zero_anchor) > 1.0e-12,
                ),
                np.divide(
                    np.abs(feasible - zero_anchor),
                    zero_anchor - lower,
                    out=np.zeros_like(feasible),
                    where=(zero_anchor - lower) > 1.0e-12,
                ),
            )
            bound_contact = (
                np.abs(normalized) >= 0.70 - 1.0e-12
            )
            row.update(
                {
                    "normalized_action": normalized.tolist(),
                    "controller_action": controller_action.tolist(),
                    "common_action": common_action.tolist(),
                    "differential_action": differential_action.tolist(),
                    "lower_power_system_pu": lower.tolist(),
                    "upper_power_system_pu": upper.tolist(),
                    "zero_anchor_power_system_pu": zero_anchor.tolist(),
                    "feasible_power_system_pu": feasible.tolist(),
                    "headroom_fraction": headroom_fraction.tolist(),
                    "bound_contact": [bool(value) for value in bound_contact],
                }
            )
            rows.append(row)
            previous_power_system_pu = np.asarray(
                row["commanded_power_system_pu"], dtype=float
            )
            current_soc = np.asarray(row["soc"], dtype=float)
            if row["tds_failed"]:
                failure = "TDS failed"
                break
    except Exception as exc:  # retained in the immutable attempt
        failure = f"{type(exc).__name__}: {exc}"
    finally:
        port_env.close()
    return {
        "phase": str(job["phase"]),
        "arm_id": str(job["arm_id"]),
        "experiment_kind": str(job["experiment_kind"]),
        "condition_id": str(job["condition_id"]),
        "delta_u": dict(job["delta_u"]),
        "input_mode": job["input_mode"],
        "sign": job["sign"],
        "identity": identity or {},
        "steps": rows,
        "completed_steps": len(rows),
        "tds_failed": failure is not None
        or any(bool(row["tds_failed"]) for row in rows),
        "failure": failure,
        "reward_used_for_gate": False,
        "training_executed": False,
    }


def _manifest_entry(path: Path, digest: str) -> dict[str, str]:
    return {"path": _relative(path), "sha256": digest}


def execute(*, expected_sha256: str) -> str:
    _assert_wsl_scratch()
    seal, seal_digest = _load_seal(expected_sha256)
    other = _other_research_python_processes()
    if other:
        raise RuntimeError(f"other research Python processes are active: {other}")
    if DEFAULT_OUT.exists():
        raise FileExistsError(f"R376 output collision: {DEFAULT_OUT}")
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
        development_records = [
            _run_job(job, contract=contract)
            for job in phase_jobs("development", contract=contract)
        ]
        development_execution_path = DEFAULT_OUT / "development_execution.json"
        development_execution_digest = _write_new_json(
            development_execution_path,
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "seal_sha256": seal_digest,
                "record_count": len(development_records),
                "records": development_records,
                "reward_used_for_gate": False,
                "training_executed": False,
            },
        )
        entries.append(
            _manifest_entry(
                development_execution_path,
                development_execution_digest,
            )
        )
        development_phase = summarize_phase_records(
            development_records,
            phase="development",
            contract=contract,
        )
        selection = select_development_candidate(
            development_phase["arm_summaries"],
            contract=contract,
        )
        development_analysis_path = DEFAULT_OUT / "development_analysis.json"
        development_analysis_digest = _write_new_json(
            development_analysis_path,
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "seal_sha256": seal_digest,
                "development": development_phase,
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
        if selection["classification"] == "DEVELOPMENT-CANDIDATE-SELECTED":
            evaluation_records = [
                _run_job(job, contract=contract)
                for job in phase_jobs(
                    "evaluation",
                    selected_arm_id=str(selected),
                    contract=contract,
                )
            ]
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
                "development_analysis_sha256": development_analysis_digest,
                "development_selection": selection,
                "evaluation": evaluation_phase,
                "wall_seconds": time.perf_counter() - started,
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


def _load_seal(expected_sha256: str) -> tuple[dict[str, Any], str]:
    seal = _read_hashed_json(SEAL)
    digest = _sha256_file(SEAL)
    if digest != expected_sha256:
        raise RuntimeError("R376 expected seal hash does not match")
    if seal.get("contract_sha256") != _payload_sha256(seal["contract"]):
        raise RuntimeError("R376 sealed contract hash mismatch")
    if seal.get("sources") != _source_manifest():
        raise RuntimeError("R376 source drift after seal")
    if seal.get("parents") != _parent_manifest():
        raise RuntimeError("R376 parent drift after seal")
    if seal.get("rehearsal_sha256") != _sha256_file(REHEARSAL):
        raise RuntimeError("R376 rehearsal drift after seal")
    if seal.get("capacity_sha256") != _sha256_file(CAPACITY):
        raise RuntimeError("R376 capacity drift after seal")
    if not _contract_is_closed(seal["contract"]):
        raise RuntimeError("R376 sealed contract is not closed")
    return seal, digest


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
