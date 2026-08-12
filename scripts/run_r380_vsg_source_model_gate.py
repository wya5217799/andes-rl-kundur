"""Prepare and run the sealed R380 four-VSG source-model gate.

The development canary constructs only the P0 source model. Rehearsal performs
the exact static pre-attempt checks without creating a seal, source model, or
trajectory. Formal execution is serial, create-only, and has no training,
tuning, retry, model-order selection, or controller surface.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"
os.environ["DISABLE_TOGGLER"] = "1"

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from andes_rl_kundur.evaluation.model_first_input_bridge import SampledInputModel
from andes_rl_kundur.evaluation.vsg_energy_port_source_adapter import (
    AndesVSGEnergyPortFixedStateSource,
)
from andes_rl_kundur.evaluation.vsg_energy_port_source_bridge import (
    derive_vsg_energy_port_input_bridge,
)
from andes_rl_kundur.evaluation.vsg_energy_port_source_model import (
    VSGEnergyPortSourceModelResult,
    construct_vsg_energy_port_source_model,
)
from probes.r380_vsg_source_model_gate import (
    POINTS,
    analyse_validation_records,
    input_sequence,
    record_guards,
    record_specs,
)


ROUND_ID = "R380"
PLAN = ROOT / "memory/rounds/R380/plan.md"
REHEARSAL = ROOT / "memory/rounds/R380/rehearsal.json"
CAPACITY_ANCHOR = ROOT / "memory/rounds/R379/capacity_evidence.json"
CAPACITY = ROOT / "memory/rounds/R380/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R380/formal_seal.json"
CANARY_OUT = ROOT / "tmp/r380_source_model_canary"
DEFAULT_OUT = ROOT / "results/research_loop/r380_vsg_source_model_gate"
LOAD_IDS = ("PQ_0", "PQ_1", "PQ_Bus14")
VSG_IDS = ("VSG_1", "VSG_2", "VSG_3", "VSG_4")
FD_STEPS = (1.0e-4, 1.0e-5, 1.0e-6)
EXPECTED_INSTALLED_SOURCES = {
    "genbase": "423dcd590748d328fe8a3ad7e41ff321810a790a476d4fab41066305d54d5702",
    "group": "139e172b31e96fa7e92ee8909feca704253702a3e9b5ea6c3df12b54d46b9697",
}


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _payload_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _write_new_json(path: Path, payload: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _canonical_bytes(payload)
    with path.open("xb") as handle:
        handle.write(data)
    digest = hashlib.sha256(data).hexdigest()
    sidecar = path.with_name(path.name + ".sha256")
    with sidecar.open("x", encoding="ascii", newline="\n") as handle:
        handle.write(f"{digest}  {path.name}\n")
    return digest


def _read_hashed_json(path: Path) -> dict[str, Any]:
    sidecar = path.with_name(path.name + ".sha256")
    expected = sidecar.read_text(encoding="ascii").split()[0]
    observed = _sha256_file(path)
    if observed != expected:
        raise RuntimeError(f"hash mismatch for {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return payload


def build_contract() -> dict[str, Any]:
    """Return the complete prospective R380 scientific contract."""

    bank = list(record_specs())
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "object": "four independent VSG SynGen.pref/tm0 energy ports",
        "points": {
            "P0": {"pq_bus15_p0_system_pu": 0.0},
            "P1": {"pq_bus15_p0_system_pu": 0.05},
        },
        "control_inputs": list(VSG_IDS),
        "disturbance_inputs": list(LOAD_IDS),
        "declared_load_baselines_system_pu": {
            "PQ_0": 11.59,
            "PQ_1": 15.75,
            "PQ_Bus14": 2.48,
        },
        "nominal_frequency_hz": 60.0,
        "sample_period_seconds": 0.2,
        "finite_difference_steps_system_pu": list(FD_STEPS),
        "model_order": "full-order",
        "validation": {
            "record_count": len(bank),
            "records_per_point": 18,
            "nonzero_record_count": 32,
            "steps_per_record": 125,
            "pulse_steps": [5, 9],
            "records": bank,
        },
        "thresholds": {
            "adjacent_derivative_relative_difference_max": 1.0e-5,
            "midpoint_ratio_max": 1.0e-6,
            "algebraic_reciprocal_condition_min": 1.0e-12,
            "eig_relative_frobenius_error_max": 1.0e-8,
            "eig_maximum_absolute_error_max": 1.0e-9,
            "control_markov_rank": 4,
            "nrmse_max": 0.15,
            "peak_vector_residual_max": 0.20,
            "zero_repeatability_hz_max": 1.0e-9,
        },
        "numeric_atol": 1.0e-12,
        "host_process_budget": 1,
        "wsl_python_processes": 1,
        "native_threads_per_process": 1,
        "other_reserved_processes": 0,
        "retry_authorized": False,
        "training_authorized": False,
        "controller_authorized": False,
        "validation_data_used_for_model_construction": False,
    }


def _contract_is_closed(contract: Mapping[str, Any]) -> bool:
    try:
        records = contract["validation"]["records"]
        baseline = contract["declared_load_baselines_system_pu"]
        return bool(
            contract["round"] == ROUND_ID
            and contract["points"]
            == {
                "P0": {"pq_bus15_p0_system_pu": 0.0},
                "P1": {"pq_bus15_p0_system_pu": 0.05},
            }
            and contract["control_inputs"] == list(VSG_IDS)
            and contract["disturbance_inputs"] == list(LOAD_IDS)
            and contract["finite_difference_steps_system_pu"] == list(FD_STEPS)
            and contract["sample_period_seconds"] == 0.2
            and records == list(record_specs())
            and len(records) == 36
            and min(float(baseline[name]) for name in LOAD_IDS) - 0.02 >= 0.0
            and contract["host_process_budget"] == 1
            and contract["wsl_python_processes"] == 1
            and contract["native_threads_per_process"] == 1
            and contract["other_reserved_processes"] == 0
            and contract["retry_authorized"] is False
            and contract["training_authorized"] is False
            and contract["controller_authorized"] is False
        )
    except (KeyError, TypeError, ValueError):
        return False


def _source_manifest() -> dict[str, dict[str, str]]:
    sources = {
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_r380_vsg_source_model_runner.py",
        "probe": ROOT / "probes/r380_vsg_source_model_gate.py",
        "probe_tests": ROOT / "tests/test_r380_vsg_source_model_gate.py",
        "source_bridge": ROOT
        / "src/andes_rl_kundur/evaluation/vsg_energy_port_source_bridge.py",
        "source_bridge_tests": ROOT / "tests/test_vsg_energy_port_source_bridge.py",
        "source_adapter": ROOT
        / "src/andes_rl_kundur/evaluation/vsg_energy_port_source_adapter.py",
        "source_adapter_tests": ROOT / "tests/test_vsg_energy_port_source_adapter.py",
        "source_model": ROOT
        / "src/andes_rl_kundur/evaluation/vsg_energy_port_source_model.py",
        "source_model_tests": ROOT / "tests/test_vsg_energy_port_source_model.py",
        "descriptor_math": ROOT
        / "src/andes_rl_kundur/evaluation/model_first_input_bridge.py",
        "fd_contract": ROOT
        / "src/andes_rl_kundur/env/andes/model_first_contract.py",
        "fd_contract_tests": ROOT / "tests/test_model_first_contract.py",
        "plan": PLAN,
        "line": ROOT / "paper/paralleled_vsg_marl/LINE.md",
        "route": ROOT / "paper/paralleled_vsg_marl/ROUTE.md",
        "energy_port": ROOT / "src/andes_rl_kundur/control/vsg_energy_port.py",
        "energy_port_environment": ROOT
        / "src/andes_rl_kundur/env/andes/vsg_energy_port_env.py",
        "v4_environment": ROOT
        / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
        "base_environment": ROOT / "src/andes_rl_kundur/env/andes/base_env.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "dependencies": ROOT / "pyproject.toml",
    }
    return {
        name: {"path": _relative(path), "sha256": _sha256_file(path)}
        for name, path in sources.items()
    }


def _parent_manifest() -> dict[str, dict[str, str]]:
    parents = {
        "object_claim": ROOT / "memory/claims/CLM-1000.md",
        "authority_claim": ROOT / "memory/claims/CLM-1005.md",
        "gate_b_claim": ROOT / "memory/claims/CLM-1010.md",
        "gate_b3_claim": ROOT / "memory/claims/CLM-1040.md",
        "object_analysis": ROOT
        / "results/research_loop/r371_vsg_energy_port_design/analysis_v5.json",
        "capacity_anchor": CAPACITY_ANCHOR,
    }
    return {
        name: {"path": _relative(path), "sha256": _sha256_file(path)}
        for name, path in parents.items()
    }


def _installed_runtime() -> dict[str, Any]:
    import andes
    from andes.models import group
    from andes.models.synchronous import genbase

    case_path = Path(andes.get_case("kundur/kundur_full.xlsx")).resolve()
    source_paths = {
        "genbase": Path(genbase.__file__).resolve(),
        "group": Path(group.__file__).resolve(),
    }
    installed_sources = {
        name: {"path": str(path), "sha256": _sha256_file(path)}
        for name, path in source_paths.items()
    }
    for name, expected in EXPECTED_INSTALLED_SOURCES.items():
        if installed_sources[name]["sha256"] != expected:
            raise RuntimeError(f"installed ANDES {name} source hash drift")
    return {
        "python": sys.version,
        "python_executable": str(Path(sys.executable).resolve()),
        "andes_version": str(getattr(andes, "__version__", "unknown")),
        "andes_module": str(Path(andes.__file__).resolve()),
        "case_path": str(case_path),
        "case_sha256": _sha256_file(case_path),
        "installed_sources": installed_sources,
    }


def _runtime_identity_matches(
    runtime: Mapping[str, Any], anchor_runtime: Mapping[str, Any]
) -> bool:
    return all(
        runtime.get(field) == anchor_runtime.get(field)
        for field in ("andes_version", "case_sha256")
    )


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("R380 ANDES commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R380 must run through scripts/andes_scratch.py")


def _other_research_python_processes() -> list[dict[str, Any]]:
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
        if "python" in lowered and "andes-rl-kundur" in lowered and (
            "run_r" in lowered or "train" in lowered or "eval" in lowered
        ):
            matches.append({"pid": pid, "command": command.strip()})
    return matches


def _memory_resources() -> tuple[int, int, int]:
    logical_processors = int(os.cpu_count() or 1)
    meminfo: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        name, separator, value = line.partition(":")
        if separator:
            meminfo[name] = int(value.strip().split()[0]) * 1024
    wsl_available = int(meminfo.get("MemAvailable", 0))
    try:
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        physical_memory = int(completed.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        physical_memory = int(meminfo.get("MemTotal", 0))
    if min(logical_processors, physical_memory, wsl_available) <= 0:
        raise RuntimeError("failed to capture positive host/WSL resources")
    return logical_processors, physical_memory, wsl_available


def _projected_artifact_bytes() -> int:
    row = {
        "step_index": 0,
        "time": 0.2,
        "control_system_pu": [0.0] * 4,
        "disturbance_system_pu": [0.0] * 3,
        "frequency_deviation_hz": [0.0] * 4,
        "requested_power_system_pu": [0.0] * 4,
        "commanded_power_system_pu": [0.0] * 4,
        "sampled_omega_pu": [1.0] * 4,
        "baseline_pref_system_pu": [0.5] * 4,
        "pref_written_system_pu": [0.5] * 4,
        "pref_readback_system_pu": [0.5] * 4,
        "torque_readback_system_pu": [0.5] * 4,
        "achieved_power_system_pu": [0.0] * 4,
        "load_readback_system_pu": [11.59, 15.75, 2.48],
        "saturation_reasons": [[], [], [], []],
        "md_action_norm": [[0.0, 0.0]] * 4,
        "tds_failed": False,
    }
    record = {
        "record_id": "P0_zero_0",
        "rows": [row] * 125,
        "frequency_deviation_hz": [[0.0] * 4] * 125,
        "guards": {"placeholder": True},
    }
    source_placeholder = {
        "descriptor": {
            "f_x": [[0.0] * 120] * 120,
            "f_y": [[0.0] * 180] * 120,
            "g_x": [[0.0] * 120] * 180,
            "g_y": [[0.0] * 180] * 180,
        },
        "sampled_model": {"state_matrix": [[0.0] * 120] * 120},
    }
    payload_bytes = (
        36 * len(_canonical_bytes(record))
        + 2 * len(_canonical_bytes(source_placeholder))
    )
    return payload_bytes + 256 * 1024


def _build_capacity_payload(
    *,
    anchor: Mapping[str, Any],
    anchor_sha256: str,
    runtime: Mapping[str, Any],
    logical_processors: int,
    physical_memory_bytes: int,
    wsl_memory_available_bytes: int,
    projected_artifact_bytes: int,
    disk_free_bytes: int,
    other_processes: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    anchor_host = anchor.get("host", {})
    anchor_wsl = anchor.get("wsl", {})
    checks = {
        "anchor_ready": anchor.get("readiness") == "RUN-READY",
        "anchor_serial": anchor.get("host_process_budget") == 1
        and anchor.get("wsl_python_processes") == 1
        and anchor.get("native_threads_per_process") == 1
        and anchor.get("other_reserved_processes") == 0,
        "current_host": logical_processors
        == int(anchor_host.get("logical_processors", -1))
        and physical_memory_bytes
        == int(anchor_host.get("physical_memory_bytes", -1)),
        "runtime_match": _runtime_identity_matches(
            runtime, anchor.get("installed_runtime", {})
        ),
        "memory_fit": wsl_memory_available_bytes
        >= 0.8 * int(anchor_wsl.get("memory_available_bytes", 0)),
        "artifact_fit": disk_free_bytes > projected_artifact_bytes,
        "competing_process_absence": not other_processes,
    }
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "readiness": "RUN-READY" if all(checks.values()) else "HOLD",
        "checks": checks,
        "capacity_anchor": {
            "path": _relative(CAPACITY_ANCHOR),
            "sha256": anchor_sha256,
        },
        "host": {
            "logical_processors": logical_processors,
            "physical_memory_bytes": physical_memory_bytes,
        },
        "wsl": {"memory_available_bytes": wsl_memory_available_bytes},
        "artifact_projection": {
            "projected_bytes": projected_artifact_bytes,
            "disk_free_bytes": disk_free_bytes,
        },
        "formal_projection": {
            "record_count": 36,
            "environment_steps": 4500,
        },
        "host_process_budget": 1,
        "wsl_python_processes": 1,
        "native_threads_per_process": 1,
        "other_reserved_processes": 0,
        "other_processes": [dict(process) for process in other_processes],
        "installed_runtime": dict(runtime),
        "scientific_classification_inspected": False,
        "formal_authority": False,
        "training_executed": False,
    }


def _rehearsal_checks(payload: Mapping[str, Any]) -> bool:
    checks = payload.get("checks")
    if not isinstance(checks, Mapping) or not checks:
        return False
    negative_checks = {
        "seal_created",
        "formal_attempt_created",
        "source_model_created",
        "physical_trajectory_executed",
    }
    return all(
        value is False if name in negative_checks else value is True
        for name, value in checks.items()
    ) and negative_checks.issubset(checks)


def rehearse() -> tuple[str, str]:
    """Run the same static pre-attempt path without a seal or model."""

    _assert_wsl_scratch()
    collisions = [
        path for path in (REHEARSAL, CAPACITY, SEAL, DEFAULT_OUT) if path.exists()
    ]
    if collisions:
        raise FileExistsError(f"R380 pre-attempt artifact exists: {collisions}")
    sources = _source_manifest()
    parents = _parent_manifest()
    runtime = _installed_runtime()
    anchor = _read_hashed_json(CAPACITY_ANCHOR)
    logical, physical_memory, wsl_available = _memory_resources()
    projection = _projected_artifact_bytes()
    disk_free = int(shutil.disk_usage(ROOT).free)
    other = _other_research_python_processes()
    capacity = _build_capacity_payload(
        anchor=anchor,
        anchor_sha256=_sha256_file(CAPACITY_ANCHOR),
        runtime=runtime,
        logical_processors=logical,
        physical_memory_bytes=physical_memory,
        wsl_memory_available_bytes=wsl_available,
        projected_artifact_bytes=projection,
        disk_free_bytes=disk_free,
        other_processes=other,
    )
    contract = build_contract()
    plan_text = PLAN.read_text(encoding="utf-8")
    checks = {
        "source_hash": bool(sources),
        "parent_hash": bool(parents),
        "installed_package": runtime["andes_version"] == "2.0.0"
        and all(
            runtime["installed_sources"][name]["sha256"] == expected
            for name, expected in EXPECTED_INSTALLED_SOURCES.items()
        ),
        "installed_case": Path(runtime["case_path"]).is_file()
        and runtime["case_sha256"]
        == "f725e03ba12d8207616f68acdd606bbd35e7c4a68f13e66d7db43925adac2ed8",
        "active_plan": "state: active" in plan_text
        and "manuscript_line: paralleled-vsg-marl" in plan_text,
        "contract_closed": _contract_is_closed(contract),
        "capacity_ready": capacity["readiness"] == "RUN-READY",
        "output_absence": not DEFAULT_OUT.exists()
        and not SEAL.exists()
        and not REHEARSAL.exists()
        and not CAPACITY.exists(),
        "competing_process_absence": not other,
        "seal_created": False,
        "formal_attempt_created": False,
        "source_model_created": False,
        "physical_trajectory_executed": False,
    }
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "readiness": "RUN-READY" if _rehearsal_checks({"checks": checks}) else "HOLD",
        "contract_sha256": _payload_sha256(contract),
        "sources": sources,
        "parents": parents,
        "installed_runtime": runtime,
        "checks": checks,
        "formal_authority": False,
        "training_executed": False,
    }
    if payload["readiness"] != "RUN-READY" or capacity["readiness"] != "RUN-READY":
        raise RuntimeError(
            f"R380 rehearsal HOLD: rehearsal={checks}, capacity={capacity['checks']}"
        )
    rehearsal_digest = _write_new_json(REHEARSAL, payload)
    capacity_digest = _write_new_json(CAPACITY, capacity)
    return rehearsal_digest, capacity_digest


def prepare() -> str:
    """Bind a passing rehearsal and capacity record into the final seal."""

    if SEAL.exists() or DEFAULT_OUT.exists():
        raise FileExistsError("R380 seal or formal output already exists")
    rehearsal = _read_hashed_json(REHEARSAL)
    capacity = _read_hashed_json(CAPACITY)
    if rehearsal.get("readiness") != "RUN-READY" or not _rehearsal_checks(rehearsal):
        raise RuntimeError("R380 rehearsal is not RUN-READY")
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R380 capacity gate is not RUN-READY")
    sources = _source_manifest()
    parents = _parent_manifest()
    runtime = _installed_runtime()
    if sources != rehearsal["sources"] or parents != rehearsal["parents"]:
        raise RuntimeError("R380 source or parent drift after rehearsal")
    if runtime != rehearsal["installed_runtime"]:
        raise RuntimeError("R380 installed runtime drift after rehearsal")
    contract = build_contract()
    if not _contract_is_closed(contract):
        raise RuntimeError("R380 contract is not closed")
    if _payload_sha256(contract) != rehearsal["contract_sha256"]:
        raise RuntimeError("R380 contract drift after rehearsal")
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract": contract,
        "contract_sha256": _payload_sha256(contract),
        "sources": sources,
        "parents": parents,
        "installed_runtime": runtime,
        "rehearsal_sha256": _sha256_file(REHEARSAL),
        "capacity_sha256": _sha256_file(CAPACITY),
        "launch": {
            "host_process_budget": 1,
            "wsl_python_processes": 1,
            "native_threads_per_process": 1,
            "other_reserved_processes": 0,
        },
        "formal_artifacts_create_only": True,
        "retry_authorized": False,
        "training_authorized": False,
        "controller_authorized": False,
    }
    return _write_new_json(SEAL, payload)


def _new_energy_port_environment(point: str) -> Any:
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.env.andes.vsg_energy_port_env import AndesVSGEnergyPortEnv

    if point not in POINTS:
        raise ValueError(f"unknown R380 point: {point}")
    point_baseline = float(build_contract()["points"][point]["pq_bus15_p0_system_pu"])

    class R380PointEnvironment(AndesMultiVSGEnvV4):
        def _pre_setup_addons(self, system: Any) -> None:
            super()._pre_setup_addons(system)
            indices = [str(value) for value in system.PQ.idx.v]
            if indices.count("PQ_Bus15") != 1:
                raise RuntimeError("R380 requires one PQ_Bus15 device")
            system.PQ.set("p0", "PQ_Bus15", point_baseline, attr="v")

    base_env = R380PointEnvironment(
        random_disturbance=False,
        comm_fail_prob=0.0,
        comm_delay_steps=0,
    )
    base_env.seed(42)
    base_env.STEPS_PER_EPISODE = 125
    return AndesVSGEnergyPortEnv(base_env=base_env)


def _array_payload(values: object) -> list[Any]:
    return np.asarray(values).tolist()


def _model_payload(model: SampledInputModel) -> dict[str, Any]:
    return {
        "state_matrix": _array_payload(model.state_matrix),
        "control_input_matrix": _array_payload(model.input_matrix[:, :4]),
        "disturbance_input_matrix": _array_payload(model.input_matrix[:, 4:]),
        "output_matrix": _array_payload(model.output_matrix),
        "control_feedthrough_matrix": _array_payload(model.feedthrough_matrix[:, :4]),
        "disturbance_feedthrough_matrix": _array_payload(
            model.feedthrough_matrix[:, 4:]
        ),
    }


def _model_from_payload(payload: Mapping[str, Any]) -> SampledInputModel:
    return SampledInputModel(
        state_matrix=np.asarray(payload["state_matrix"], dtype=float),
        input_matrix=np.hstack(
            (
                np.asarray(payload["control_input_matrix"], dtype=float),
                np.asarray(payload["disturbance_input_matrix"], dtype=float),
            )
        ),
        output_matrix=np.asarray(payload["output_matrix"], dtype=float),
        feedthrough_matrix=np.hstack(
            (
                np.asarray(payload["control_feedthrough_matrix"], dtype=float),
                np.asarray(payload["disturbance_feedthrough_matrix"], dtype=float),
            )
        ),
    )


def _construction_payload(
    *,
    point: str,
    source: AndesVSGEnergyPortFixedStateSource,
    result: VSGEnergyPortSourceModelResult,
) -> dict[str, Any]:
    snapshot = source.descriptor_snapshot
    descriptor = {
        "time_constants": _array_payload(snapshot.time_constants),
        "f_x": _array_payload(snapshot.f_x),
        "f_y": _array_payload(snapshot.f_y),
        "g_x": _array_payload(snapshot.g_x),
        "g_y": _array_payload(snapshot.g_y),
        "state_names": list(snapshot.state_names),
        "algebraic_names": list(snapshot.algebraic_names),
        "eig_state_matrix": _array_payload(snapshot.eig_state_matrix),
        "eig_state_names": list(snapshot.eig_state_names),
        "frequency_output_map": _array_payload(snapshot.frequency_output_map),
        "omega_state_addresses": _array_payload(snapshot.omega_state_addresses),
        "equilibrium_x": _array_payload(snapshot.equilibrium_x),
        "equilibrium_y": _array_payload(snapshot.equilibrium_y),
        "equilibrium_z": _array_payload(snapshot.equilibrium_z),
        "equilibrium_f": _array_payload(snapshot.equilibrium_f),
        "equilibrium_g": _array_payload(snapshot.equilibrium_g),
        "initialization_residual_tolerance": (
            snapshot.initialization_residual_tolerance
        ),
        "initialization_max_abs_f": snapshot.initialization_max_abs_f,
        "initialization_max_abs_g": snapshot.initialization_max_abs_g,
        "eig_eigenvalues_real": _array_payload(np.real(snapshot.eig_eigenvalues)),
        "eig_eigenvalues_imag": _array_payload(np.imag(snapshot.eig_eigenvalues)),
        "positive_real_tolerance": snapshot.positive_real_tolerance,
        "positive_real_count": snapshot.positive_real_count,
    }
    return {
        "point": point,
        "object_valid": True,
        "construction_pass": result.passed,
        "error": result.error,
        "binding": {
            "vsg_port_ids": list(source.binding.vsg_port_ids),
            "pq_load_ids": list(source.binding.pq_load_ids),
            "sampled_omega_pu": _array_payload(source.binding.sampled_omega_pu),
            "pq_load_baselines_system_pu": _array_payload(
                source.baseline_load_system_pu
            ),
            "pq_bus15_p0_system_pu": float(
                source.system.PQ.get("p0", "PQ_Bus15", attr="v")
            ),
            "source_fingerprint": source.binding.source_fingerprint,
            "port_semantics": source.binding.port_semantics,
        },
        "metrics": result.metrics,
        "dynamic_state_names": result.dynamic_state_names,
        "descriptor": descriptor,
        "sampled_model": (
            None if result.sampled_model is None else _model_payload(result.sampled_model)
        ),
    }


def _construct_point_model(
    point: str, *, source_fingerprint: str
) -> tuple[dict[str, Any], SampledInputModel | None]:
    environment = _new_energy_port_environment(point)
    try:
        environment.reset(delta_u={})
        source = AndesVSGEnergyPortFixedStateSource.from_initialized_energy_port_env(
            environment,
            pq_load_ids=LOAD_IDS,
            source_fingerprint=source_fingerprint,
        )
        bridges = tuple(
            derive_vsg_energy_port_input_bridge(
                binding=source.binding,
                source=source,
                step_system_pu=step,
            )
            for step in FD_STEPS
        )
        result = construct_vsg_energy_port_source_model(
            snapshot=source.descriptor_snapshot,
            bridges=bridges,
        )
        return (
            _construction_payload(point=point, source=source, result=result),
            result.sampled_model,
        )
    finally:
        environment.close()


def canary(*, out_dir: Path = CANARY_OUT) -> str:
    """Construct only the P0 development source model and no TDS trace."""

    _assert_wsl_scratch()
    target = out_dir / "canary.json"
    if out_dir.exists():
        raise FileExistsError(f"R380 development canary collision: {out_dir}")
    runtime = _installed_runtime()
    fingerprint = _payload_sha256(
        {
            "purpose": "R380-DEVELOPMENT-SOURCE-ONLY",
            "point": "P0",
            "runtime": runtime,
            "sources": _source_manifest(),
        }
    )
    started = time.perf_counter()
    payload, model = _construct_point_model("P0", source_fingerprint=fingerprint)
    canary_payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "evidence_status": "DEVELOPMENT-SOURCE-ONLY",
        "created_utc": datetime.now(UTC).isoformat(),
        "wall_seconds": time.perf_counter() - started,
        "point": "P0",
        "passed": payload["object_valid"] is True
        and payload["construction_pass"] is True
        and model is not None,
        "binding": payload["binding"],
        "metrics": payload["metrics"],
        "dynamic_state_count": len(payload["dynamic_state_names"]),
        "sampled_model_shapes": (
            None
            if model is None
            else {
                "A": list(model.state_matrix.shape),
                "B": list(model.input_matrix.shape),
                "C": list(model.output_matrix.shape),
                "D": list(model.feedthrough_matrix.shape),
            }
        ),
        "physical_trajectory_executed": False,
        "scientific_classification_inspected": False,
        "formal_authority": False,
        "training_executed": False,
    }
    digest = _write_new_json(target, canary_payload)
    if canary_payload["passed"] is not True:
        raise RuntimeError(f"R380 development source canary failed: {payload['error']}")
    return digest


def _port_row(
    info: Mapping[str, Any],
    *,
    step_index: int,
    control: np.ndarray,
    disturbance: np.ndarray,
    load_readback: np.ndarray,
) -> dict[str, Any]:
    def values(key: str) -> list[Any]:
        return np.asarray(info[key], dtype=float).tolist()

    return {
        "step_index": step_index,
        "time": float(info["time"]),
        "control_system_pu": control.tolist(),
        "disturbance_system_pu": disturbance.tolist(),
        "requested_power_system_pu": values(
            "vsg_energy_port_requested_power_system_pu"
        ),
        "commanded_power_system_pu": values(
            "vsg_energy_port_commanded_power_system_pu"
        ),
        "sampled_omega_pu": values("vsg_energy_port_sampled_omega_pu"),
        "baseline_pref_system_pu": values(
            "vsg_energy_port_baseline_pref_system_pu"
        ),
        "pref_written_system_pu": values("vsg_energy_port_pref_written_system_pu"),
        "pref_readback_system_pu": values(
            "vsg_energy_port_pref_readback_system_pu"
        ),
        "torque_readback_system_pu": values(
            "vsg_energy_port_torque_readback_system_pu"
        ),
        "achieved_power_system_pu": values(
            "vsg_energy_port_achieved_power_system_pu"
        ),
        "load_readback_system_pu": load_readback.tolist(),
        "saturation_reasons": [
            list(reasons) for reasons in info["vsg_energy_port_saturation_reasons"]
        ],
        "omega": values("omega"),
        "freq_hz_physical": values("freq_hz_physical"),
        "P_es": values("P_es"),
        "delta_M": values("delta_M"),
        "delta_D": values("delta_D"),
        "md_action_norm": values("vsg_energy_port_md_action_norm"),
        "tds_failed": bool(info["tds_failed"]),
    }


def _run_record(
    spec: Mapping[str, Any], *, seal_sha256: str, runtime: Mapping[str, Any]
) -> dict[str, Any]:
    point = str(spec["point"])
    inputs = input_sequence(spec)
    environment = _new_energy_port_environment(point)
    base_env = environment.base_env
    rows: list[dict[str, Any]] = []
    identity: dict[str, Any] = {}
    load_baseline = np.zeros(3, dtype=float)
    failure: str | None = None
    try:
        environment.reset(delta_u={})
        load_positions = np.asarray(
            [int(base_env.ss.PQ.idx2uid(name)) for name in LOAD_IDS], dtype=int
        )
        load_baseline = np.asarray(base_env.ss.PQ.Ppf.v, dtype=float)[
            load_positions
        ].copy()
        identity = {
            "point": point,
            "vsg_idx": [str(value) for value in base_env.vsg_idx],
            "vsg_buses": [
                int(base_env.ss.GENCLS.bus.v[position])
                for position in base_env._vsg_pos
            ],
            "pq_load_ids": list(LOAD_IDS),
            "pq_bus15_p0_system_pu": float(
                base_env.ss.PQ.get("p0", "PQ_Bus15", attr="v")
            ),
            "pflow_converged": base_env.ss.PFlow.converged is True,
            "tds_test_ok": base_env.ss.TDS.test_ok is True,
            "exit_code": int(np.asarray(base_env.ss.exit_code).reshape(-1)[0]),
            "seal_sha256": seal_sha256,
            "case_sha256": runtime["case_sha256"],
            "andes_version": runtime["andes_version"],
        }
        for step_index, values in enumerate(inputs):
            control = values[:4]
            disturbance = values[4:]
            target_load = load_baseline + disturbance
            if np.any(target_load < 0.0):
                raise ValueError("R380 record would create a negative physical load")
            for device_id, value in zip(LOAD_IDS, target_load, strict=True):
                base_env.ss.PQ.set("Ppf", device_id, float(value), attr="v")
            base_env.ss.TDS.custom_event = True
            _observation, _reward, _done, info = environment.step(control)
            load_readback = np.asarray(base_env.ss.PQ.Ppf.v, dtype=float)[
                load_positions
            ].copy()
            rows.append(
                _port_row(
                    info,
                    step_index=step_index,
                    control=control,
                    disturbance=disturbance,
                    load_readback=load_readback,
                )
            )
            if bool(info["tds_failed"]):
                failure = "TDS failed"
                break
    except Exception as exc:
        failure = f"{type(exc).__name__}: {exc}"
    finally:
        environment.close()
    guards = record_guards(
        rows=rows,
        expected_inputs=inputs,
        point=point,
        identity=identity,
        load_baseline=load_baseline,
        seal_sha256=seal_sha256,
        runtime=runtime,
        failure=failure,
        contract=build_contract(),
    )
    return {
        "record_id": str(spec["record_id"]),
        "point": point,
        "kind": str(spec["kind"]),
        "identity": identity,
        "failure": failure,
        "completed_steps": len(rows),
        "rows": rows,
        "frequency_deviation_hz": [
            (np.asarray(row["freq_hz_physical"], dtype=float) - 60.0).tolist()
            for row in rows
        ],
        "guards": guards,
        "reward_used_for_gate": False,
        "training_executed": False,
    }


def _load_seal(expected_sha256: str) -> tuple[dict[str, Any], str]:
    seal = _read_hashed_json(SEAL)
    digest = _sha256_file(SEAL)
    if digest != expected_sha256:
        raise RuntimeError("R380 expected seal hash does not match")
    if seal.get("contract_sha256") != _payload_sha256(seal["contract"]):
        raise RuntimeError("R380 sealed contract hash mismatch")
    if seal.get("contract") != build_contract() or not _contract_is_closed(
        seal["contract"]
    ):
        raise RuntimeError("R380 contract drift after seal")
    if seal.get("sources") != _source_manifest():
        raise RuntimeError("R380 source drift after seal")
    if seal.get("parents") != _parent_manifest():
        raise RuntimeError("R380 parent drift after seal")
    if seal.get("installed_runtime") != _installed_runtime():
        raise RuntimeError("R380 installed runtime drift after seal")
    if seal.get("rehearsal_sha256") != _sha256_file(REHEARSAL):
        raise RuntimeError("R380 rehearsal drift after seal")
    if seal.get("capacity_sha256") != _sha256_file(CAPACITY):
        raise RuntimeError("R380 capacity drift after seal")
    return seal, digest


def _manifest_entry(path: Path, digest: str) -> dict[str, str]:
    return {"path": _relative(path), "sha256": digest}


def _write_terminal_manifest(entries: Sequence[Mapping[str, str]]) -> str:
    return _write_new_json(
        DEFAULT_OUT / "formal_manifest.json",
        {"schema_version": 1, "round": ROUND_ID, "entries": list(entries)},
    )


def _construct_models_first_failure(
    *,
    seal_sha256: str,
    runtime: Mapping[str, Any],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, SampledInputModel],
    bool,
]:
    """Construct points in order and stop at the first object/model failure."""

    constructions: dict[str, dict[str, Any]] = {}
    models: dict[str, SampledInputModel] = {}
    object_valid = True
    for point in POINTS:
        fingerprint = _payload_sha256(
            {
                "round": ROUND_ID,
                "point": point,
                "seal_sha256": seal_sha256,
                "runtime": runtime,
            }
        )
        try:
            payload, model = _construct_point_model(
                point,
                source_fingerprint=fingerprint,
            )
        except Exception as exc:
            object_valid = False
            payload = {
                "point": point,
                "object_valid": False,
                "construction_pass": False,
                "error": f"{type(exc).__name__}: {exc}",
                "sampled_model": None,
            }
            model = None
        constructions[point] = payload
        if model is not None:
            models[point] = model
        if not object_valid or payload.get("construction_pass") is not True:
            break
    return constructions, models, object_valid


def _run_validation_records_first_failure(
    *,
    specs: Sequence[Mapping[str, Any]],
    seal_sha256: str,
    runtime: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Execute the bank in order and stop after the first invalid record."""

    records: list[dict[str, Any]] = []
    for spec in specs:
        record = _run_record(spec, seal_sha256=seal_sha256, runtime=runtime)
        records.append(record)
        guards = record.get("guards")
        if not isinstance(guards, Mapping) or not guards or not all(
            value is True for value in guards.values()
        ):
            break
    return records


def execute(*, expected_sha256: str) -> str:
    """Run the one authorized sealed construction and validation attempt."""

    _assert_wsl_scratch()
    seal, seal_digest = _load_seal(expected_sha256)
    other = _other_research_python_processes()
    if other:
        raise RuntimeError(f"other research Python processes are active: {other}")
    if DEFAULT_OUT.exists():
        raise FileExistsError(f"R380 output collision: {DEFAULT_OUT}")
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
            "controller_authorized": False,
        },
    )
    entries = [_manifest_entry(attempt_path, attempt_digest)]
    started = time.perf_counter()
    try:
        runtime = seal["installed_runtime"]
        constructions, models, object_valid = _construct_models_first_failure(
            seal_sha256=seal_digest,
            runtime=runtime,
        )
        construction_path = DEFAULT_OUT / "formal_source_models.json"
        construction_digest = _write_new_json(
            construction_path,
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "seal_sha256": seal_digest,
                "points": constructions,
                "validation_trajectories_inspected": False,
                "training_executed": False,
            },
        )
        entries.append(_manifest_entry(construction_path, construction_digest))
        construction_pass = object_valid and set(models) == set(POINTS) and all(
            payload.get("construction_pass") is True
            for payload in constructions.values()
        )
        if not object_valid or not construction_pass:
            classification = (
                "INVALID-OBJECT-OR-PORT" if not object_valid else "STOP-SOURCE-MODEL"
            )
            analysis_path = DEFAULT_OUT / "formal_analysis.json"
            analysis_digest = _write_new_json(
                analysis_path,
                {
                    "schema_version": 1,
                    "round": ROUND_ID,
                    "seal_sha256": seal_digest,
                    "source_models_sha256": construction_digest,
                    "classification": classification,
                    "validity_pass": object_valid,
                    "construction_pass": construction_pass,
                    "validation_records_executed": 0,
                    "validation_prediction_metrics_inspected": False,
                    "wall_seconds": time.perf_counter() - started,
                    "training_authorized": False,
                    "controller_authorized": False,
                },
            )
            entries.append(_manifest_entry(analysis_path, analysis_digest))
            _write_terminal_manifest(entries)
            print(f"classification={classification}", flush=True)
            return analysis_digest

        records = _run_validation_records_first_failure(
            specs=seal["contract"]["validation"]["records"],
            seal_sha256=seal_digest,
            runtime=runtime,
        )
        execution_path = DEFAULT_OUT / "formal_validation_records.json"
        execution_digest = _write_new_json(
            execution_path,
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "seal_sha256": seal_digest,
                "source_models_sha256": construction_digest,
                "record_count": len(records),
                "records": records,
                "training_executed": False,
            },
        )
        entries.append(_manifest_entry(execution_path, execution_digest))
        analysis = analyse_validation_records(
            models=models,
            records=records,
            construction_pass=True,
        )
        analysis.update(
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "seal_sha256": seal_digest,
                "source_models_sha256": construction_digest,
                "validation_records_sha256": execution_digest,
                "wall_seconds": time.perf_counter() - started,
                "training_authorized": False,
                "physical_controller_authorized": False,
            }
        )
        analysis_path = DEFAULT_OUT / "formal_analysis.json"
        analysis_digest = _write_new_json(analysis_path, analysis)
        entries.append(_manifest_entry(analysis_path, analysis_digest))
        _write_terminal_manifest(entries)
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
                "classification": "INVALID-OBJECT-OR-PORT",
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
    commands.add_parser("canary")
    commands.add_parser("rehearse")
    commands.add_parser("prepare")
    formal = commands.add_parser("execute")
    formal.add_argument("--expected-seal-sha256", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "canary":
        print(f"canary_sha256={canary()}")
    elif args.command == "rehearse":
        rehearsal_digest, capacity_digest = rehearse()
        print(f"rehearsal_sha256={rehearsal_digest}")
        print(f"capacity_sha256={capacity_digest}")
    elif args.command == "prepare":
        print(f"seal_sha256={prepare()}")
    elif args.command == "execute":
        print(f"analysis_sha256={execute(expected_sha256=args.expected_seal_sha256)}")
    else:  # pragma: no cover
        raise RuntimeError(f"unknown command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
