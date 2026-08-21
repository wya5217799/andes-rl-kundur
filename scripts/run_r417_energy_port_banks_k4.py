"""Sealed WSL runner for R415 (feedback-loop K=4.0 breadth check on the frozen A4 unseen blocks (second R408-disclosed development candidate)): energy-port extra banks.

Owner-authorized by the soft-spot experiment program
(``paper/yang_md_decoupling_marl/working/soft_spot_experiment_program.md``,
item A4, creative mode): run the second R408-disclosed candidate (bandpass K=4.0) plus the R379
references on the three frozen unseen condition blocks of
``andes_rl_kundur/evaluation/soft_spot_energy_port_banks.py`` (new
probe/disturbance set, and two M-D plant perturbations).  Endpoints use the
frozen R409 thresholds (r_d <= 0.95, r_cross <= 1.10, all R379 guards),
candidate-versus-local on the same block.

The item's serial estimate is <= 20 minutes, so per the parallelism gate it
runs the existing single-process seam: no shard driver, one WSL python
process (sealed budget 1).

Lifecycle (WSL only, always through the scratch launcher):
  python scripts/andes_scratch.py scripts/run_r417_energy_port_banks_k4.py measure-capacity
  python scripts/andes_scratch.py scripts/run_r417_energy_port_banks_k4.py rehearse
  python scripts/andes_scratch.py scripts/run_r417_energy_port_banks_k4.py prepare
  python scripts/andes_scratch.py scripts/run_r417_energy_port_banks_k4.py execute
  python scripts/andes_scratch.py scripts/run_r417_energy_port_banks_k4.py classify

All formal artifacts are create-only with sha256 sidecars under
results/research_loop/r417_energy_port_banks_k4/.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

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
for _bootstrap_path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from andes_rl_kundur.control.active_power import (  # noqa: E402
    r272_frozen_bess_contract,
)
from andes_rl_kundur.control.feasibility_native_vsg_action import (  # noqa: E402
    FeasibilityNativeVSGActionMap,
)
from andes_rl_kundur.evaluation.gate_b3_deterministic import (  # noqa: E402
    build_contract as _base_contract,
    phase_jobs,
    probe_request,
    summarize_phase_records,
)
from andes_rl_kundur.evaluation.soft_spot_energy_port_banks import (  # noqa: E402
    BLOCKS,
    DIFFERENTIAL_RATIO_MAX,
    EVAL_ARMS,
    LOCAL_ARM,
    PROBE_CROSS_RATIO_MAX,
    STRICT_CROSS_RATIO_MAX,
    ZERO_ARM,
    block_by_id,
    block_ids,
)
from scripts.run_r408_v2_solving_gate import (  # noqa: E402
    _enrich_row,
    _make_controller,
)
from scripts.run_r372_energy_port_object_gate import (  # noqa: E402
    _identity,
    _port_row,
)
from run_r401_cd_matd3_canary_contract import (  # noqa: E402
    _memory_resources,
    _other_research_python_processes,
)

CANDIDATE_ARM = "bandpass_k4"
EVAL_ARMS = (ZERO_ARM, LOCAL_ARM, CANDIDATE_ARM)

ROUND_ID = "R417"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
PLAN = ROOT / "memory/rounds/R417/plan.md"
REHEARSAL = ROOT / "memory/rounds/R417/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R417/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R417/formal_seal.json"
OUT = ROOT / "results/research_loop/r417_energy_port_banks_k4"
R408_OUT = ROOT / "results/research_loop/r408_v2_solving_gate"
R409_OUT = ROOT / "results/research_loop/r409_heldout_gate"

CAPACITY_TASKS = 32


def safe_emit(message: str, *, stream: TextIO | None = None) -> bool:
    target = sys.stdout if stream is None else stream
    try:
        print(message, file=target, flush=True)
    except BrokenPipeError:
        if stream is None:
            sys.stdout = open(os.devnull, "w", encoding="utf-8")
        return False
    return True


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _write_new_json(path: Path, payload: Mapping[str, Any]) -> str:
    if path.exists() or Path(f"{path}.sha256").exists():
        raise FileExistsError(f"refusing to overwrite create-only artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    path.write_text(text + "\n", encoding="utf-8")
    digest = _sha256_file(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def _read_hashed_json(path: Path) -> dict[str, Any]:
    sidecar = Path(f"{path}.sha256")
    if not path.is_file() or not sidecar.is_file():
        raise FileNotFoundError(f"missing hashed JSON: {path}")
    expected = sidecar.read_text(encoding="ascii").split()[0]
    actual = _sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"hash mismatch: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("R417 physical commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R415 must run through scripts/andes_scratch.py")
    import torch

    torch.set_num_threads(1)
    if torch.get_num_interop_threads() != 1:
        try:
            torch.set_num_interop_threads(1)
        except RuntimeError:
            pass


def build_block_contract(block: Mapping[str, Any]) -> dict[str, Any]:
    contract = _base_contract()
    contract["round"] = ROUND_ID
    contract["development"]["arm_ids"] = list(EVAL_ARMS)
    contract["development"]["probe_condition"] = {
        "condition_id": str(block["probe_condition"]["condition_id"]),
        "delta_u": dict(block["probe_condition"]["delta_u"]),
    }
    contract["development"]["disturbance_conditions"] = [
        {
            "condition_id": str(condition["condition_id"]),
            "delta_u": dict(condition["delta_u"]),
        }
        for condition in block["disturbance_conditions"]
    ]
    contract["development"]["record_count"] = (
        len(EVAL_ARMS) * (len(contract["probe_arm_ids"]) + 2)
    )
    contract["training_authorized"] = False
    contract["r415"] = {
        "block_id": str(block["block_id"]),
        "kind": str(block["kind"]),
        "vsg_m0": float(block["vsg_m0"]),
        "d0_per_agent": [float(value) for value in block["d0_per_agent"]],
    }
    return contract


def _expected_identity(contract: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "n_agents": int(contract["device_count"]),
        "vsg_idx": list(contract["expected_vsg_idx"]),
        "vsg_buses": list(contract["expected_vsg_buses"]),
    }


def _run_job(
    job: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    block: Mapping[str, Any],
) -> dict[str, Any]:
    """R408-faithful record loop with the block's plant config."""
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.env.andes.v4_config import V4Config
    from andes_rl_kundur.env.andes.vsg_energy_port_env import AndesVSGEnergyPortEnv

    base_env = AndesMultiVSGEnvV4(
        random_disturbance=False,
        comm_fail_prob=0.0,
        config=V4Config(
            vsg_m0=float(block["vsg_m0"]),
            d0_per_agent=tuple(float(value) for value in block["d0_per_agent"]),
        ),
        comm_delay_steps=0,
    )
    base_env.seed(int(contract["seed"]))
    base_env.STEPS_PER_EPISODE = int(contract["steps"])
    port_env = AndesVSGEnergyPortEnv(base_env=base_env)
    action_map = FeasibilityNativeVSGActionMap(r272_frozen_bess_contract())
    controller = _make_controller(str(job["arm_id"]), contract)
    rows: list[dict[str, Any]] = []
    identity: dict[str, Any] = {}
    failure: str | None = None
    previous_power_system_pu = np.zeros(4, dtype=float)
    current_soc = np.full(4, float(contract["soc_initial"]), dtype=float)
    try:
        port_env.reset(delta_u=dict(job["delta_u"]))
        identity = _identity(base_env)
        for _step_index in range(int(contract["steps"])):
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
            row = _port_row(info, step_index=_step_index, done=bool(done))
            row = _enrich_row(
                row,
                normalized=normalized,
                controller_action=controller_action,
                common_action=common_action,
                differential_action=differential_action,
                mapped=mapped,
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
        "identity": identity,
        "steps": rows,
        "completed_steps": len(rows),
        "tds_failed": failure is not None
        or any(bool(row["tds_failed"]) for row in rows),
        "failure": failure,
        "reward_used_for_gate": False,
        "training_executed": False,
    }


def _block_summary(
    records: Sequence[Mapping[str, Any]], contract: Mapping[str, Any]
) -> dict[str, Any]:
    phase = summarize_phase_records(
        list(records), phase="development", contract=contract
    )
    local = phase["arm_summaries"][LOCAL_ARM]
    candidate = phase["arm_summaries"][CANDIDATE_ARM]
    zero = phase["arm_summaries"][ZERO_ARM]
    local_diff = float(
        local["disturbance"]["mean_differential_frequency_energy_hz2_s"]
    )
    local_off = float(local["probe"]["off_diagonal_response_energy_hz2_s"])
    diff_ratio = (
        float(candidate["disturbance"]["mean_differential_frequency_energy_hz2_s"])
        / local_diff
        if local_diff > 0.0
        else float("inf")
    )
    cross_ratio = (
        float(candidate["probe"]["off_diagonal_response_energy_hz2_s"])
        / local_off
        if local_off > 0.0
        else float("inf")
    )
    passed = bool(
        diff_ratio <= DIFFERENTIAL_RATIO_MAX
        and cross_ratio <= PROBE_CROSS_RATIO_MAX
        and candidate["guards_pass"]
        and local["guards_pass"]
        and zero["guards_pass"]
    )
    return {
        "differential_ratio": diff_ratio,
        "probe_cross_ratio": cross_ratio,
        "strict_cross_pass": bool(cross_ratio <= STRICT_CROSS_RATIO_MAX),
        "candidate_guards_pass": bool(candidate["guards_pass"]),
        "reference_guards_pass": bool(local["guards_pass"] and zero["guards_pass"]),
        "guard_errors": list(candidate["guard_errors"]),
        "passed": passed,
        "local_differential_energy": local_diff,
        "local_probe_off_diagonal_energy": local_off,
        "record_count": len(records),
    }


def _run_block(block: Mapping[str, Any]) -> dict[str, Any]:
    contract = build_block_contract(block)
    records = [
        _run_job(job, contract=contract, block=block)
        for job in phase_jobs("development", contract=contract)
    ]
    for record in records:
        if dict(record.get("identity", {})) != _expected_identity(contract):
            raise ValueError(f"{block['block_id']}: VSG identity drift")
    return {
        "block_id": str(block["block_id"]),
        "contract_round": ROUND_ID,
        "records": records,
    }


def _source_manifest() -> dict[str, dict[str, str]]:
    sources = {
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_run_r417_energy_port_banks_k4.py",
        "banks": ROOT
        / "src/andes_rl_kundur/evaluation/soft_spot_energy_port_banks.py",
        "r408_runner": ROOT / "scripts/run_r408_v2_solving_gate.py",
        "r409_runner": ROOT / "scripts/run_r409_heldout_gate.py",
        "r372_runner": ROOT / "scripts/run_r372_energy_port_object_gate.py",
        "contract": ROOT
        / "src/andes_rl_kundur/evaluation/gate_b3_deterministic.py",
        "bandpass_controller": ROOT
        / "src/andes_rl_kundur/control/ring_bandpass_damping.py",
        "v4_environment": ROOT
        / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
        "v4_config": ROOT / "src/andes_rl_kundur/env/andes/v4_config.py",
        "energy_port_environment": ROOT
        / "src/andes_rl_kundur/env/andes/vsg_energy_port_env.py",
        "port_map": ROOT
        / "src/andes_rl_kundur/control/feasibility_native_vsg_action.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "dependencies": ROOT / "pyproject.toml",
    }
    return {
        name: {"path": _relative(path), "sha256": _sha256_file(path)}
        for name, path in sources.items()
    }


def _parent_manifest() -> dict[str, dict[str, str]]:
    parents = {
        "r408_formal_analysis": R408_OUT / "formal_analysis.json",
        "r408_formal_manifest": R408_OUT / "formal_manifest.json",
        "r409_formal_analysis": R409_OUT / "formal_analysis.json",
        "r409_formal_manifest": R409_OUT / "formal_manifest.json",
        "program": ROOT
        / "paper/yang_md_decoupling_marl/working/soft_spot_experiment_program.md",
        "owner_decision": ROOT
        / "paper/yang_md_decoupling_marl/working"
        / "route_owner_decision_soft_spot_program_2026-08-16.md",
        "r408_feed": ROOT / "paper/yang_md_decoupling_marl/reports/R408.md",
        "r409_feed": ROOT / "paper/yang_md_decoupling_marl/reports/R409.md",
    }
    return {
        name: {"path": _relative(path), "sha256": _sha256_file(path)}
        for name, path in parents.items()
    }


def _installed_runtime() -> dict[str, Any]:
    import andes

    case_path = Path(andes.get_case("kundur/kundur_full.xlsx")).resolve()
    return {
        "python": sys.version,
        "python_executable": str(Path(sys.executable).resolve()),
        "andes_version": str(getattr(andes, "__version__", "unknown")),
        "andes_module": str(Path(andes.__file__).resolve()),
        "case_path": str(case_path),
        "case_sha256": _sha256_file(case_path),
    }


def _other_processes() -> list[dict[str, Any]]:
    own_pids = {os.getpid()}
    parent = int(os.getppid())
    while parent > 1 and len(own_pids) < 16:
        own_pids.add(parent)
        try:
            stat_fields = Path(f"/proc/{parent}/stat").read_text(
                encoding="utf-8"
            ).split()
            parent = int(stat_fields[3])
        except (OSError, ValueError, IndexError):
            break
    matches: list[dict[str, Any]] = []
    for entry in _other_research_python_processes():
        if int(entry["pid"]) in own_pids:
            continue
        command = str(entry.get("command", ""))
        if any(
            marker in command
            for marker in (
                "run_r410_message_repair.py",
                "run_r411_probe_amplitude_ladder.py",
                "run_r412_topology_robustness.py",
                "run_r417_energy_port_banks_k4.py",
                "soft_spot_shard_driver.py",
            )
        ):
            continue
        matches.append(entry)
    return matches


def _authority_checks() -> dict[str, bool]:
    plan_text = PLAN.read_text(encoding="utf-8")
    line_text = LINE.read_text(encoding="utf-8")
    contract = _base_contract()
    return {
        "active_plan": "state: active" in plan_text
        and "manuscript_line: yang-md-decoupling-marl" in plan_text
        and "R417" in plan_text,
        "active_line": "line_id: yang-md-decoupling-marl" in line_text
        and "status: active" in line_text,
        "contract_shape": len(contract["mode_ids"]) == 4
        and int(contract["device_count"]) == 4
        and int(contract["steps"]) == 50,
        "banks_frozen": len(BLOCKS) == 3 and block_ids()[0] == "a4_conditions_b",
        "output_absence": not OUT.exists(),
    }


def _capacity_task(_task_index: int) -> dict[str, Any]:
    import resource

    block = block_by_id("a4_conditions_b")
    contract = build_block_contract(block)
    job = phase_jobs("development", contract=contract)[0]
    record = _run_job(job, contract=contract, block=block)
    return {
        "completed": bool(
            record["completed_steps"] > 0 and not record["tds_failed"]
        ),
        "tds_failed": bool(record["tds_failed"]),
        "failure": record["failure"],
        "worker_max_rss_kib": int(
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        ),
    }


def measure_capacity() -> str:
    _assert_wsl_scratch()
    for candidate in (CAPACITY, REHEARSAL, SEAL):
        if candidate.exists():
            raise FileExistsError(f"R417 pre-attempt artifact exists: {candidate}")
    if OUT.exists():
        raise FileExistsError("R417 formal output exists before capacity")
    other = _other_processes()
    if other:
        raise RuntimeError(
            "other research Python processes are active: " + str(other)
        )
    logical, physical_memory, wsl_available = _memory_resources()
    started = time.perf_counter()
    results = [_capacity_task(index) for index in range(CAPACITY_TASKS)]
    wall_seconds = time.perf_counter() - started
    valid = all(
        result["completed"] is True and result["tds_failed"] is False
        for result in results
    )
    return _write_new_json(
        CAPACITY,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "readiness": "RUN-READY" if valid else "HOLD",
            "stage": "serial_single_process_anchor_32_tasks",
            "authorization": (
                "owner-authorized soft-spot A4; serial estimate <= 20 min, "
                "plain seam, one WSL python process"
            ),
            "representative_task": {
                "block_id": "a4_conditions_b",
                "tasks": CAPACITY_TASKS,
            },
            "serial_anchor": {
                "wall_seconds": wall_seconds,
                "task_count": CAPACITY_TASKS,
                "valid_completions": sum(
                    result["completed"] is True and result["tds_failed"] is False
                    for result in results
                ),
                "all_records_valid": bool(valid),
                "throughput_jobs_per_second": CAPACITY_TASKS / wall_seconds,
                "maximum_worker_rss_bytes": max(
                    int(result["worker_max_rss_kib"]) * 1024 for result in results
                ),
                "failures": [
                    {"task": index, "failure": result["failure"]}
                    for index, result in enumerate(results)
                    if result["completed"] is not True
                    or result["tds_failed"] is not False
                ],
            },
            "host": {
                "logical_processors": logical,
                "physical_memory_bytes": physical_memory,
            },
            "wsl": {"memory_available_bytes": wsl_available},
            "whole_host_python_process_budget": 1,
            "host_process_budget": 1,
            "wsl_python_processes": 1,
            "selected_workers": 0,
            "rung_decisions": [],
            "empirical_anchor": {
                "all_records_valid": bool(valid),
                "concurrent_workers": 1,
                "launcher_processes": 0,
                "native_threads_per_worker": 1,
                "source": "serial representative anchor (32 tasks, one process)",
            },
            "native_threads_per_process": 1,
            "other_reserved_processes": 0,
            "other_processes": other,
            "memory_rule": (
                "single serial process; the anchor's measured RSS must not "
                "exceed half of WSL total memory"
            ),
            "capacity_trace_role": "non_claim_bearing_excluded_from_evidence",
            "sources": _source_manifest(),
            "installed_runtime": _installed_runtime(),
            "scientific_classification_inspected": False,
            "formal_authority": False,
            "training_executed": False,
        },
    )


def rehearse() -> str:
    _assert_wsl_scratch()
    for candidate in (REHEARSAL, SEAL):
        if candidate.exists():
            raise FileExistsError(f"R417 pre-attempt artifact exists: {candidate}")
    if not CAPACITY.exists():
        raise FileExistsError("capacity evidence must exist before rehearse")
    checks = _authority_checks()
    required = {
        "active_plan",
        "active_line",
        "contract_shape",
        "banks_frozen",
        "output_absence",
    }
    if not all(checks.get(key) is True for key in required):
        raise RuntimeError("R417 rehearsal checks failed: " + str(checks))
    runtime = _installed_runtime()
    sources = _source_manifest()
    parents = _parent_manifest()
    checks["source_hash"] = bool(sources)
    checks["parent_hash"] = bool(parents)
    checks["installed_package"] = runtime["andes_version"] != "unknown"
    checks["installed_case"] = Path(runtime["case_path"]).is_file()
    block = block_by_id("a4_conditions_b")
    contract = build_block_contract(block)
    job = phase_jobs("development", contract=contract)[0]
    record = _run_job(job, contract=contract, block=block)
    if not record["completed_steps"] or record["tds_failed"]:
        raise RuntimeError("R417 rehearsal trajectory failed")
    return _write_new_json(
        REHEARSAL,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "sources": sources,
            "parents": parents,
            "installed_runtime": runtime,
            "checks": checks,
            "rehearsal_record": {
                "completed_steps": record["completed_steps"],
                "tds_failed": record["tds_failed"],
                "identity_ok": dict(record.get("identity", {}))
                == _expected_identity(contract),
            },
            "physical_trajectory_executed": True,
            "formal_artifacts_created": False,
            "training_executed": False,
        },
    )


def _plan_process_budget_matches(capacity: Mapping[str, Any]) -> bool:
    plan_text = PLAN.read_text(encoding="utf-8")
    return bool(
        "host_process_budget: 1" in plan_text
        and "wsl_python_processes: 1" in plan_text
        and "native_threads_per_process: 1" in plan_text
        and "other_reserved_processes: 0" in plan_text
    )


def prepare() -> str:
    _assert_wsl_scratch()
    rehearsal = _read_hashed_json(REHEARSAL)
    capacity = _read_hashed_json(CAPACITY)
    snapshot_sources = _source_manifest()
    snapshot_parents = _parent_manifest()
    snapshot_runtime = _installed_runtime()
    checks = _authority_checks()
    required = {
        "active_plan",
        "active_line",
        "contract_shape",
        "banks_frozen",
        "output_absence",
    }
    if not all(checks.get(key) is True for key in required):
        raise RuntimeError("R417 authority checks failed: " + str(checks))
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R417 capacity gate is not RUN-READY")
    if not _plan_process_budget_matches(capacity):
        raise RuntimeError("R417 plan does not freeze the serial process budget")
    for payload in (rehearsal, capacity):
        if payload["sources"] != snapshot_sources:
            raise RuntimeError("R417 source drift before seal")
        if payload["installed_runtime"] != snapshot_runtime:
            raise RuntimeError("R417 runtime drift before seal")
    if rehearsal["parents"] != snapshot_parents:
        raise RuntimeError("R417 parent drift before seal")
    if SEAL.exists() or OUT.exists():
        raise FileExistsError("R417 formal artifact exists before sealing")
    return _write_new_json(
        SEAL,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "blocks": _blocks_canonical(),
            "thresholds": {
                "differential_ratio_max": DIFFERENTIAL_RATIO_MAX,
                "probe_cross_ratio_max": PROBE_CROSS_RATIO_MAX,
                "strict_cross_ratio_max": STRICT_CROSS_RATIO_MAX,
            },
            "sources": snapshot_sources,
            "parents": snapshot_parents,
            "installed_runtime": snapshot_runtime,
            "plan_sha256": _sha256_file(PLAN),
            "line_sha256": _sha256_file(LINE),
            "rehearsal_sha256": _sha256_file(REHEARSAL),
            "capacity_sha256": _sha256_file(CAPACITY),
            "single_factor_change": (
                "per block exactly one unseen condition factor versus the "
                "frozen banks (one new probe/disturbance set, or one M-D "
                "plant perturbation); the K=3.5 bandpass, references, "
                "estimators, thresholds, and guards are R408/R409 assets "
                "read-only"
            ),
            "launch": {
                "host_process_budget": 1,
                "wsl_python_processes": 1,
                "worker_processes": 0,
                "native_threads_per_process": 1,
                "other_reserved_processes": 0,
            },
            "formal_artifacts_create_only": True,
            "retry_authorized": False,
            "training_authorized_in_this_round": False,
        },
    )


def _blocks_canonical() -> list[dict[str, Any]]:
    """JSON-round-tripped block list (tuples become lists), so the seal
    content and the load-time comparison share one canonical form."""
    return json.loads(
        json.dumps([dict(block) for block in BLOCKS], separators=(",", ":"))
    )


def load_seal() -> dict[str, Any]:
    seal = _read_hashed_json(SEAL)
    if seal.get("round") != ROUND_ID:
        raise RuntimeError("seal belongs to another round")
    if seal.get("blocks") != _blocks_canonical():
        raise RuntimeError("frozen banks drifted from the R417 seal")
    for name, entry in (seal.get("sources") or {}).items():
        if entry["sha256"] != _sha256_file(ROOT / entry["path"]):
            raise RuntimeError(f"source drifted from the R417 seal: {name}")
    return seal


def execute() -> str:
    _assert_wsl_scratch()
    load_seal()
    checks = _authority_checks()
    if not checks["output_absence"]:
        raise FileExistsError("R417 formal output root already exists")
    attempt_digest = _write_new_json(
        OUT / "formal_attempt.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "blocks": block_ids(),
            "thresholds": {
                "differential_ratio_max": DIFFERENTIAL_RATIO_MAX,
                "probe_cross_ratio_max": PROBE_CROSS_RATIO_MAX,
                "strict_cross_ratio_max": STRICT_CROSS_RATIO_MAX,
            },
            "training_authorized": False,
            "held_out_accessed": True,
        },
    )
    for block in BLOCKS:
        folder = OUT / str(block["block_id"])
        payload = _run_block(block)
        _write_new_json(folder / "records.json", payload)
    return attempt_digest


def classify() -> str:
    _assert_wsl_scratch()
    load_seal()
    summaries = {}
    for block in BLOCKS:
        block_id = str(block["block_id"])
        payload = _read_hashed_json(OUT / block_id / "records.json")
        contract = build_block_contract(block)
        summaries[block_id] = {
            "block": dict(block),
            "summary": _block_summary(payload["records"], contract),
        }
    passing = [
        block_id for block_id, row in summaries.items() if row["summary"]["passed"]
    ]
    analysis = {
        "schema_version": 1,
        "round": ROUND_ID,
        "manuscript_line": "yang-md-decoupling-marl",
        "created_utc": datetime.now(UTC).isoformat(),
        "seal_sha256": _sha256_file(SEAL),
        "thresholds": {
            "differential_ratio_max": DIFFERENTIAL_RATIO_MAX,
            "probe_cross_ratio_max": PROBE_CROSS_RATIO_MAX,
            "strict_cross_ratio_max": STRICT_CROSS_RATIO_MAX,
        },
        "blocks": summaries,
        "passing_blocks": passing,
        "pass_count": len(passing),
        "block_count": len(BLOCKS),
        "verdict": (
            "ALL-BLOCKS-PASS" if len(passing) == len(BLOCKS) else "BLOCKS-FAIL"
        ),
        "reward_used_for_gate": False,
        "training_executed": False,
    }
    analysis_path = OUT / "formal_analysis.json"
    digest = _write_new_json(analysis_path, analysis)
    manifest_payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "analysis_sha256": digest,
        "input_artifacts": [
            {"path": _relative(path), "sha256": _sha256_file(path)}
            for path in sorted(OUT.rglob("*.json"))
            if path.name not in {"formal_analysis.json", "formal_manifest.json"}
        ],
        "block_count": len(BLOCKS),
    }
    _write_new_json(OUT / "formal_manifest.json", manifest_payload)
    return digest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "measure-capacity",
            "rehearse",
            "prepare",
            "execute",
            "classify",
        ],
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "measure-capacity":
        safe_emit(f"R417 capacity evidence: {measure_capacity()}")
    elif args.command == "rehearse":
        safe_emit(f"R417 rehearsal artifact: {rehearse()}")
    elif args.command == "prepare":
        safe_emit(f"R417 formal seal: {prepare()}")
    elif args.command == "execute":
        safe_emit(f"R417 formal attempt: {execute()}")
    else:
        safe_emit(f"R417 formal analysis: {classify()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
