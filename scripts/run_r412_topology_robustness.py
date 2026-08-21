"""Sealed WSL runner for R412 (soft-spot program A2): topology robustness.

Owner-authorized by the soft-spot experiment program
(``paper/yang_md_decoupling_marl/working/soft_spot_experiment_program.md``,
item A2, creative mode): re-evaluate the frozen K=3.5 bandpass and its
references (zero_feedback / local_feasibility_native) on a frozen variant
bank of the modified Kundur (line outages + tie-impedance changes, N=12).
Outages enter only through ``apply_line_outage()`` (ANDES ``Model.set``);
impedance variants scale ``Line.x`` through ``Model.set``.  Every variant's
paper-facing equilibrium passes the CLM-0665 hard gate
(``eig_validity_guard``: ``TDS.test_ok``, ``exit_code=0``, initialization
residuals, finite spectrum, positive-real guard) and its value is recorded
per variant.  Endpoints use the frozen R409 thresholds (r_d <= 0.95,
r_cross <= 1.10, all R379 guards).

The nominal variant re-executes the disclosed R408 development bank and is
the pre-registered base-case anchor: its r_d / r_cross must reproduce the
R408 values (0.938947 / 0.539791) within 1e-6 relative.

Lifecycle (WSL only, always through the scratch launcher):
  python scripts/andes_scratch.py scripts/run_r412_topology_robustness.py inventory
  python scripts/andes_scratch.py scripts/run_r412_topology_robustness.py measure-capacity
  python scripts/andes_scratch.py scripts/run_r412_topology_robustness.py rehearse
  python scripts/andes_scratch.py scripts/run_r412_topology_robustness.py prepare
  python scripts/andes_scratch.py scripts/run_r412_topology_robustness.py shards
  python scripts/andes_scratch.py scripts/run_r412_topology_robustness.py shard <variant_id> [--resume]
  python scripts/andes_scratch.py scripts/run_r412_topology_robustness.py classify

All formal artifacts are create-only with sha256 sidecars under
results/research_loop/r412_topology_robustness/.
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
from concurrent.futures import ProcessPoolExecutor
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
    LOCAL_ARM,
    ZERO_ARM,
    build_contract as _base_contract,
    phase_jobs,
    probe_request,
    summarize_phase_records,
)
from andes_rl_kundur.evaluation.topology_status import (  # noqa: E402
    apply_line_outage,
    eig_validity_guard,
)
from scripts.run_r408_v2_solving_gate import (  # noqa: E402
    _enrich_row,
    _make_controller,
    bandpass_arm_id,
)
from scripts.run_r372_energy_port_object_gate import (  # noqa: E402
    _identity,
    _port_row,
)
from run_r401_cd_matd3_canary_contract import (  # noqa: E402
    _memory_resources,
    _other_research_python_processes,
)

ROUND_ID = "R412"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
PLAN = ROOT / "memory/rounds/R412/plan.md"
REHEARSAL = ROOT / "memory/rounds/R412/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R412/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R412/formal_seal.json"
OUT = ROOT / "results/research_loop/r412_topology_robustness"
R408_OUT = ROOT / "results/research_loop/r408_v2_solving_gate"
R409_OUT = ROOT / "results/research_loop/r409_heldout_gate"

CANDIDATE_ARM = "bandpass_k3p5"
EVAL_ARMS = (ZERO_ARM, LOCAL_ARM, CANDIDATE_ARM)
DIFFERENTIAL_RATIO_MAX = 0.95
PROBE_CROSS_RATIO_MAX = 1.10
STRICT_CROSS_RATIO_MAX = 0.95
POSITIVE_REAL_TOLERANCE = 1.0e-7
BASE_ANCHOR_TOLERANCE_RELATIVE = 1.0e-6
BASE_ANCHOR = {"r_d": 0.938947, "r_cross": 0.539791}

# Frozen variant bank (frozen from the pre-seal inventory of the modified
# Kundur, 2026-08-17): one topology factor per variant versus nominal.
# Outages target the two inter-area corridors (7-8: Line_4/5/6, 8-9:
# Line_7/8) and one VSG tie per area; impedance variants scale one line
# reactance by 0.5 or 1.5.  Line_2 stays excluded (R305 positive-mode
# precedent).  The nominal variant must stay first.
TOPOLOGY_VARIANTS: tuple[dict[str, Any], ...] = (
    {"variant_id": "nominal", "kind": "none"},
    {"variant_id": "out_Line_4", "kind": "outage", "line_idx": "Line_4"},
    {"variant_id": "out_Line_5", "kind": "outage", "line_idx": "Line_5"},
    {"variant_id": "out_Line_7", "kind": "outage", "line_idx": "Line_7"},
    {"variant_id": "out_Line_8", "kind": "outage", "line_idx": "Line_8"},
    {"variant_id": "out_Line_7_12", "kind": "outage", "line_idx": "Line_7_12"},
    {"variant_id": "out_Line_9_15", "kind": "outage", "line_idx": "Line_9_15"},
    {"variant_id": "x0p5_Line_4", "kind": "impedance", "line_idx": "Line_4", "factor": 0.5},
    {"variant_id": "x1p5_Line_4", "kind": "impedance", "line_idx": "Line_4", "factor": 1.5},
    {"variant_id": "x0p5_Line_7", "kind": "impedance", "line_idx": "Line_7", "factor": 0.5},
    {"variant_id": "x1p5_Line_7", "kind": "impedance", "line_idx": "Line_7", "factor": 1.5},
    {"variant_id": "x1p5_Line_7_12", "kind": "impedance", "line_idx": "Line_7_12", "factor": 1.5},
)

CAPACITY_RUNGS = (1, 2, 4, 8, 12, 16)
CAPACITY_TASKS_PER_RUNG = 32
EVAL_WORKER_RSS_FLOOR_BYTES = 944214016
MARGINAL_GAIN_MIN = 1.05
MARGINAL_GAIN_CONFIRM_LOW = 1.03
MARGINAL_GAIN_CONFIRM_HIGH = 1.07


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


def variant_ids() -> list[str]:
    return [str(variant["variant_id"]) for variant in TOPOLOGY_VARIANTS]


def variant_by_id(variant_id: str) -> Mapping[str, Any]:
    for variant in TOPOLOGY_VARIANTS:
        if str(variant["variant_id"]) == variant_id:
            return variant
    raise ValueError(f"unknown variant: {variant_id}")


class TopologyVariantEnvV4:
    """Mix-in factory: an AndesMultiVSGEnvV4 with one frozen mutation applied
    after every system build, before any power flow."""

    @staticmethod
    def build_variant_env_class(variant: Mapping[str, Any]) -> type:
        from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4

        kind = str(variant["kind"])

        class _VariantEnv(AndesMultiVSGEnvV4):
            def _build_system(self):
                ss = super()._build_system()
                if kind == "outage":
                    apply_line_outage(ss, str(variant["line_idx"]))
                elif kind == "impedance":
                    line_idx = str(variant["line_idx"])
                    position = list(ss.Line.idx.v).index(line_idx)
                    current = float(ss.Line.x.v[position])
                    ss.Line.set(
                        "x", line_idx, current * float(variant["factor"]), attr="v"
                    )
                return ss

        return _VariantEnv


def _build_env(variant: Mapping[str, Any], *, seed: int, steps: int) -> Any:
    env_class = TopologyVariantEnvV4.build_variant_env_class(variant)
    env = env_class(
        random_disturbance=False,
        comm_fail_prob=0.0,
        comm_delay_steps=0,
    )
    env.seed(int(seed))
    env.STEPS_PER_EPISODE = int(steps)
    return env


def build_variant_contract(variant: Mapping[str, Any]) -> dict[str, Any]:
    contract = _base_contract()
    contract["round"] = ROUND_ID
    contract["development"]["arm_ids"] = list(EVAL_ARMS)
    contract["development"]["record_count"] = (
        len(EVAL_ARMS) * (len(contract["probe_arm_ids"]) + 2)
    )
    contract["training_authorized"] = False
    contract["r412"] = {
        "variant_id": str(variant["variant_id"]),
        "kind": str(variant["kind"]),
        "line_idx": variant.get("line_idx"),
        "factor": variant.get("factor"),
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
    variant: Mapping[str, Any],
) -> dict[str, Any]:
    """R408-faithful record loop on one topology variant (env subclass)."""
    from andes_rl_kundur.env.andes.vsg_energy_port_env import AndesVSGEnergyPortEnv

    base_env = _build_env(
        variant, seed=int(contract["seed"]), steps=int(contract["steps"])
    )
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


def _variant_readback(env: Any, variant: Mapping[str, Any]) -> dict[str, Any]:
    system = env.ss
    kind = str(variant["kind"])
    if kind == "none":
        return {"kind": "none"}
    line_idx = str(variant["line_idx"])
    if kind == "outage":
        position = list(system.Line.idx.v).index(line_idx)
        value = float(system.Line.u.v[position])
        return {
            "kind": kind,
            "line_idx": line_idx,
            "u": value,
            "u_zero_as_expected": bool(abs(value) < 1e-12),
        }
    if kind == "impedance":
        position = list(system.Line.idx.v).index(line_idx)
        value = float(system.Line.x.v[position])
        return {
            "kind": kind,
            "line_idx": line_idx,
            "x": value,
            "factor": float(variant["factor"]),
        }
    raise ValueError(f"unknown variant kind: {kind}")


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    return value


def eig_gate(variant: Mapping[str, Any]) -> dict[str, Any]:
    """Run the CLM-0665 hard gate on the variant's base equilibrium.

    Initialization or spectrum failures are scientific outcomes and must be
    recorded as gate failures, never as crashes: every step (reset, TDS
    init, EIG, guard) is captured and any exception is stored in
    ``failure`` with the gate verdict left False.
    """
    env = None
    payload: dict[str, Any] = {
        "variant_id": str(variant["variant_id"]),
        "readback": None,
        "pflow_converged": False,
        "tds_init_return": None,
        "eig_return": None,
        "failure": None,
        "passed": False,
        "initialization_pass": False,
        "tds_test_ok": False,
        "system_exit_code": None,
        "initialization_tolerance": None,
        "dae_max_abs_f": None,
        "dae_max_abs_g": None,
        "residual_pass": False,
        "spectrum_finite": False,
        "positive_real_tolerance": POSITIVE_REAL_TOLERANCE,
        "positive_real_count": None,
        "max_real": None,
        "spectrum_pass": False,
        "eigenvalue_count": 0,
    }
    try:
        env = _build_env(
            variant,
            seed=int(_base_contract()["seed"]),
            steps=int(_base_contract()["steps"]),
        )
        env.reset(delta_u=None)
        payload["pflow_converged"] = bool(
            getattr(env.ss.PFlow, "converged", False)
        )
        payload["readback"] = _variant_readback(env, variant)
        payload["tds_init_return"] = _json_safe(env.ss.TDS.init())
        payload["eig_return"] = _json_safe(env.ss.EIG.run())
        guard = eig_validity_guard(
            env.ss, positive_real_tolerance=POSITIVE_REAL_TOLERANCE
        )
        payload.update(_json_safe(guard))
        payload["eigenvalue_count"] = int(np.asarray(env.ss.EIG.mu).size)
    except Exception as exc:
        payload["failure"] = f"{type(exc).__name__}: {exc}"
    finally:
        if env is not None:
            try:
                env.close()
            except Exception:
                pass
    return payload


def _run_variant_bank(variant: Mapping[str, Any]) -> dict[str, Any]:
    contract = build_variant_contract(variant)
    records = [
        _run_job(job, contract=contract, variant=variant)
        for job in phase_jobs("development", contract=contract)
    ]
    for record in records:
        if dict(record.get("identity", {})) != _expected_identity(contract):
            raise ValueError(f"{variant['variant_id']}: VSG identity drift")
    return {
        "variant_id": str(variant["variant_id"]),
        "contract_round": ROUND_ID,
        "records": records,
    }


def _evaluate_shard(variant_id: str, *, resume: bool) -> None:
    _assert_wsl_scratch()
    load_seal()
    variant = variant_by_id(variant_id)
    folder = OUT / str(variant_id)
    gate_path = folder / "eig_gate.json"
    bank_path = folder / "records.json"
    if gate_path.exists() or bank_path.exists():
        if resume and gate_path.is_file() and bank_path.is_file():
            _read_hashed_json(gate_path)
            _read_hashed_json(bank_path)
            return
        raise FileExistsError(f"create-only output exists: {folder}")
    gate = eig_gate(variant)
    bank = _run_variant_bank(variant)
    _write_new_json(gate_path, gate)
    _write_new_json(bank_path, bank)


# ── inventory (pre-seal, prints the frozen-variant source of truth) ─────

def inventory() -> str:
    _assert_wsl_scratch()
    env = _build_env(
        {"variant_id": "nominal", "kind": "none"},
        seed=int(_base_contract()["seed"]),
        steps=int(_base_contract()["steps"]),
    )
    try:
        env.reset(delta_u=None)
        system = env.ss
        lines = []
        for index, idx in enumerate(system.Line.idx.v):
            lines.append(
                {
                    "idx": str(idx),
                    "bus1": int(system.Line.bus1.v[index]),
                    "bus2": int(system.Line.bus2.v[index]),
                    "u": float(system.Line.u.v[index]),
                    "x": float(system.Line.x.v[index]),
                }
            )
        return json.dumps(
            {
                "vsg_buses": [int(system.GENCLS.bus.v[p]) for p in env._vsg_pos],
                "vsg_idx": [str(v) for v in env.vsg_idx],
                "lines": lines,
            },
            indent=2,
            sort_keys=True,
        )
    finally:
        try:
            env.close()
        except Exception:
            pass


# ── capacity ladder ────────────────────────────────────────────────────

def _capacity_task(_task_index: int) -> dict[str, Any]:
    import resource

    contract = build_variant_contract(
        {"variant_id": "nominal", "kind": "none"}
    )
    job = phase_jobs("development", contract=contract)[0]
    record = _run_job(
        job, contract=contract, variant={"variant_id": "nominal", "kind": "none"}
    )
    return {
        "completed": bool(record["completed_steps"] > 0 and not record["tds_failed"]),
        "tds_failed": bool(record["tds_failed"]),
        "failure": record["failure"],
        "worker_max_rss_kib": int(
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        ),
    }


def _measure_rung(workers: int) -> dict[str, Any]:
    started = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as executor:
        results = list(
            executor.map(_capacity_task, range(CAPACITY_TASKS_PER_RUNG))
        )
    wall_seconds = time.perf_counter() - started
    valid = all(
        result["completed"] is True and result["tds_failed"] is False
        for result in results
    )
    return {
        "workers": workers,
        "native_threads_per_worker": 1,
        "wall_seconds": wall_seconds,
        "job_count": len(results),
        "valid_completions": sum(
            result["completed"] is True and result["tds_failed"] is False
            for result in results
        ),
        "all_records_valid": bool(valid),
        "throughput_jobs_per_second": len(results) / wall_seconds,
        "maximum_worker_rss_bytes": max(
            int(result["worker_max_rss_kib"]) * 1024 for result in results
        ),
        "failures": [
            {"task": index, "failure": result["failure"]}
            for index, result in enumerate(results)
            if result["completed"] is not True or result["tds_failed"] is not False
        ],
    }


def _select_rung(
    final_throughput: Mapping[int, float],
    *,
    wsl_available_bytes: int,
) -> dict[str, Any]:
    selected: int | None = None
    selected_throughput: float | None = None
    decisions: list[dict[str, Any]] = []
    for workers in CAPACITY_RUNGS:
        throughput = final_throughput[workers]
        projected = EVAL_WORKER_RSS_FLOOR_BYTES * workers
        memory_safe = projected <= int(wsl_available_bytes) / 2
        if not memory_safe:
            accepted, reason = False, "memory_reserve_guard"
        elif selected is None:
            accepted, reason = True, "first_safe_rung"
        elif throughput < MARGINAL_GAIN_MIN * float(selected_throughput):
            accepted, reason = False, "insufficient_throughput_gain"
        else:
            accepted, reason = True, "safe_throughput_gain"
        decisions.append(
            {
                "workers": workers,
                "accepted": accepted,
                "reason": reason,
                "projected_concurrent_worker_rss_bytes": projected,
                "memory_safe": memory_safe,
                "final_throughput_jobs_per_second": throughput,
            }
        )
        if accepted:
            selected = workers
            selected_throughput = throughput
    if selected is None:
        return {
            "readiness": "HOLD",
            "selected_workers": None,
            "host_process_budget": None,
            "wsl_python_processes": None,
            "rung_decisions": decisions,
        }
    return {
        "readiness": "RUN-READY",
        "selected_workers": selected,
        "host_process_budget": selected + 1,
        "wsl_python_processes": selected + 1,
        "selected_throughput_jobs_per_second": float(selected_throughput),
        "rung_decisions": decisions,
    }


def measure_capacity() -> str:
    _assert_wsl_scratch()
    for candidate in (CAPACITY, REHEARSAL, SEAL):
        if candidate.exists():
            raise FileExistsError(f"R412 pre-attempt artifact exists: {candidate}")
    if OUT.exists():
        raise FileExistsError("R412 formal output exists before capacity")
    other = _other_processes()
    if other:
        raise RuntimeError(
            "other research Python processes are active: " + str(other)
        )
    logical, physical_memory, wsl_available = _memory_resources()
    first_pass = [_measure_rung(workers) for workers in CAPACITY_RUNGS]
    final: dict[int, float] = {
        workers: first_pass[index]["throughput_jobs_per_second"]
        for index, workers in enumerate(CAPACITY_RUNGS)
    }
    confirm_pairs: list[tuple[int, int]] = []
    for index in range(len(CAPACITY_RUNGS) - 1):
        low = CAPACITY_RUNGS[index]
        high = CAPACITY_RUNGS[index + 1]
        gain = final[high] / max(final[low], 1e-12)
        if MARGINAL_GAIN_CONFIRM_LOW <= gain <= MARGINAL_GAIN_CONFIRM_HIGH:
            confirm_pairs.append((low, high))
    remeasure = sorted({worker for pair in confirm_pairs for worker in pair})
    second_pass: list[dict[str, Any]] = []
    if remeasure:
        second_pass = [_measure_rung(workers) for workers in remeasure]
        for workers in remeasure:
            values = [
                first_pass[CAPACITY_RUNGS.index(workers)][
                    "throughput_jobs_per_second"
                ],
                second_pass[remeasure.index(workers)]["throughput_jobs_per_second"],
            ]
            final[workers] = float(np.mean(values))
    selection = _select_rung(final, wsl_available_bytes=wsl_available)
    return _write_new_json(
        CAPACITY,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "readiness": selection["readiness"],
            "stage": "representative_eval_capacity_ladder_rungs_1_2_4_8_12_16",
            "authorization": "owner-authorized soft-spot A2 topology robustness",
            "representative_task": {
                "variant_id": "nominal",
                "arm_id": str(phase_jobs("development", contract=build_variant_contract(
                    {"variant_id": "nominal", "kind": "none"}
                ))[0]["arm_id"]),
                "tasks_per_rung": CAPACITY_TASKS_PER_RUNG,
            },
            "eval_worker_rss_floor": {
                "bytes": EVAL_WORKER_RSS_FLOOR_BYTES,
                "source": "memory/rounds/R402/capacity_evidence_v2.json",
                "role": "conservative per-worker RSS floor (R402 anchor)",
            },
            "host": {
                "logical_processors": logical,
                "physical_memory_bytes": physical_memory,
            },
            "wsl": {"memory_available_bytes": wsl_available},
            "rungs": first_pass,
            "confirmation_pairs": [
                {"low_workers": low, "high_workers": high}
                for low, high in confirm_pairs
            ],
            "confirmation_pass_2": second_pass,
            "final_throughput_jobs_per_second": final,
            **selection,
            "whole_host_python_process_budget": selection.get(
                "host_process_budget"
            ),
            "empirical_anchor": {
                "all_records_valid": True,
                "concurrent_workers": (
                    int(selection["selected_workers"]) + 1
                    if selection["selected_workers"] is not None
                    else None
                ),
                "launcher_processes": 1,
                "native_threads_per_worker": 1,
                "source": "selected representative capacity rung",
            },
            "native_threads_per_process": 1,
            "other_reserved_processes": 0,
            "other_processes": other,
            "memory_rule": (
                "projected concurrent eval-worker RSS must not exceed half "
                "of WSL total memory"
            ),
            "marginal_rule": (
                "next rung accepted only at >=5 percent marginal throughput "
                "gain; pairs within 5%+-2pp re-measured once and averaged"
            ),
            "capacity_trace_role": "non_claim_bearing_excluded_from_evidence",
            "sources": _source_manifest(),
            "installed_runtime": _installed_runtime(),
            "scientific_classification_inspected": False,
            "formal_authority": False,
            "training_executed": False,
        },
    )


# ── rehearsal / seal / classify ────────────────────────────────────────

def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("R412 physical commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R412 must run through scripts/andes_scratch.py")
    import torch

    torch.set_num_threads(1)
    if torch.get_num_interop_threads() != 1:
        try:
            torch.set_num_interop_threads(1)
        except RuntimeError:
            pass


def _source_manifest() -> dict[str, dict[str, str]]:
    sources = {
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_run_r412_topology_robustness.py",
        "shard_driver": ROOT / "scripts/soft_spot_shard_driver.py",
        "r408_runner": ROOT / "scripts/run_r408_v2_solving_gate.py",
        "r409_runner": ROOT / "scripts/run_r409_heldout_gate.py",
        "r372_runner": ROOT / "scripts/run_r372_energy_port_object_gate.py",
        "contract": ROOT
        / "src/andes_rl_kundur/evaluation/gate_b3_deterministic.py",
        "topology_gate": ROOT / "src/andes_rl_kundur/evaluation/topology_status.py",
        "topology_gate_tests": ROOT / "tests/test_topology_status.py",
        "bandpass_controller": ROOT
        / "src/andes_rl_kundur/control/ring_bandpass_damping.py",
        "v4_environment": ROOT
        / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
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
        "r408_formal_execution": R408_OUT / "formal_execution.json",
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
        and "R412" in plan_text,
        "active_line": "line_id: yang-md-decoupling-marl" in line_text
        and "status: active" in line_text,
        "contract_shape": len(contract["mode_ids"]) == 4
        and int(contract["device_count"]) == 4
        and int(contract["steps"]) == 50,
        "variant_bank_frozen": len(TOPOLOGY_VARIANTS) == 12
        and variant_ids()[0] == "nominal",
        "output_absence": not OUT.exists(),
    }


def rehearse() -> str:
    _assert_wsl_scratch()
    for candidate in (REHEARSAL, SEAL):
        if candidate.exists():
            raise FileExistsError(f"R412 pre-attempt artifact exists: {candidate}")
    if not CAPACITY.exists():
        raise FileExistsError("capacity evidence must exist before rehearse")
    checks = _authority_checks()
    required = {
        "active_plan",
        "active_line",
        "contract_shape",
        "variant_bank_frozen",
        "output_absence",
    }
    if not all(checks.get(key) is True for key in required):
        raise RuntimeError("R412 rehearsal checks failed: " + str(checks))
    runtime = _installed_runtime()
    sources = _source_manifest()
    parents = _parent_manifest()
    checks["source_hash"] = bool(sources)
    checks["parent_hash"] = bool(parents)
    checks["installed_package"] = runtime["andes_version"] != "unknown"
    checks["installed_case"] = Path(runtime["case_path"]).is_file()
    variant = variant_by_id("nominal")
    contract = build_variant_contract(variant)
    job = phase_jobs("development", contract=contract)[0]
    record = _run_job(job, contract=contract, variant=variant)
    if not record["completed_steps"] or record["tds_failed"]:
        raise RuntimeError("R412 rehearsal trajectory failed")
    gate = eig_gate(variant)
    if not gate["passed"]:
        raise RuntimeError("R412 nominal EIG rehearsal gate failed")
    # R412-abort lesson: the rehearsal must also exercise the graceful
    # failure path of the EIG gate (init-divergent variants record a gate
    # failure instead of crashing the shard).
    failure_path = {
        name: eig_gate(variant_by_id(name))
        for name in ("out_Line_4", "out_Line_7_12", "out_Line_9_15")
    }
    for name, result in failure_path.items():
        if not isinstance(result.get("passed"), bool):
            raise RuntimeError(f"R412 rehearsal eig_gate malformed: {name}")
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
            "rehearsal_eig_gate": gate,
            "rehearsal_eig_failure_path": failure_path,
            "physical_trajectory_executed": True,
            "formal_artifacts_created": False,
            "training_executed": False,
        },
    )


def _plan_process_budget_matches(capacity: Mapping[str, Any]) -> bool:
    plan_text = PLAN.read_text(encoding="utf-8")
    expected = int(capacity["wsl_python_processes"])
    return bool(
        f"host_process_budget: {expected}" in plan_text
        and f"wsl_python_processes: {expected}" in plan_text
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
        "variant_bank_frozen",
        "output_absence",
    }
    if not all(checks.get(key) is True for key in required):
        raise RuntimeError("R412 authority checks failed: " + str(checks))
    if capacity.get("readiness") != "RUN-READY":
        raise RuntimeError("R412 capacity gate is not RUN-READY")
    if not _plan_process_budget_matches(capacity):
        raise RuntimeError("R412 plan does not freeze the measured process budget")
    for payload in (rehearsal, capacity):
        if payload["sources"] != snapshot_sources:
            raise RuntimeError("R412 source drift before seal")
        if payload["installed_runtime"] != snapshot_runtime:
            raise RuntimeError("R412 runtime drift before seal")
    if rehearsal["parents"] != snapshot_parents:
        raise RuntimeError("R412 parent drift before seal")
    if SEAL.exists() or OUT.exists():
        raise FileExistsError("R412 formal artifact exists before sealing")
    process_count = int(capacity["wsl_python_processes"])
    workers = int(capacity["selected_workers"])
    return _write_new_json(
        SEAL,
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "created_utc": datetime.now(UTC).isoformat(),
            "variant_bank": [dict(variant) for variant in TOPOLOGY_VARIANTS],
            "thresholds": {
                "differential_ratio_max": DIFFERENTIAL_RATIO_MAX,
                "probe_cross_ratio_max": PROBE_CROSS_RATIO_MAX,
                "strict_cross_ratio_max": STRICT_CROSS_RATIO_MAX,
                "positive_real_tolerance": POSITIVE_REAL_TOLERANCE,
                "base_anchor_tolerance_relative": BASE_ANCHOR_TOLERANCE_RELATIVE,
            },
            "base_anchor": BASE_ANCHOR,
            "sources": snapshot_sources,
            "parents": snapshot_parents,
            "installed_runtime": snapshot_runtime,
            "plan_sha256": _sha256_file(PLAN),
            "line_sha256": _sha256_file(LINE),
            "rehearsal_sha256": _sha256_file(REHEARSAL),
            "capacity_sha256": _sha256_file(CAPACITY),
            "single_factor_change": (
                "per variant exactly one topology factor versus nominal "
                "(one opened line or one tie reactance scale); the K=3.5 "
                "bandpass, references, bank, thresholds, and guards are the "
                "R408/R409 assets read-only"
            ),
            "launch": {
                "host_process_budget": process_count,
                "wsl_python_processes": process_count,
                "worker_processes": workers,
                "native_threads_per_process": 1,
                "other_reserved_processes": 0,
            },
            "formal_artifacts_create_only": True,
            "retry_authorized": False,
            "training_authorized_in_this_round": False,
        },
    )


def load_seal() -> dict[str, Any]:
    seal = _read_hashed_json(SEAL)
    if seal.get("round") != ROUND_ID:
        raise RuntimeError("seal belongs to another round")
    if seal.get("variant_bank") != [
        dict(variant) for variant in TOPOLOGY_VARIANTS
    ]:
        raise RuntimeError("variant bank drifted from the R412 seal")
    for name, entry in (seal.get("sources") or {}).items():
        if entry["sha256"] != _sha256_file(ROOT / entry["path"]):
            raise RuntimeError(f"source drifted from the R412 seal: {name}")
    return seal


def _variant_summary(records: Sequence[Mapping[str, Any]], contract: Mapping[str, Any]) -> dict[str, Any]:
    phase = summarize_phase_records(
        list(records), phase="development", contract=contract
    )
    local = phase["arm_summaries"][LOCAL_ARM]
    candidate = phase["arm_summaries"][CANDIDATE_ARM]
    zero = phase["arm_summaries"][ZERO_ARM]
    local_diff = float(local["disturbance"]["mean_differential_frequency_energy_hz2_s"])
    local_off = float(local["probe"]["off_diagonal_response_energy_hz2_s"])
    diff_ratio = (
        float(candidate["disturbance"]["mean_differential_frequency_energy_hz2_s"])
        / local_diff
        if local_diff > 0.0
        else float("inf")
    )
    cross_ratio = (
        float(candidate["probe"]["off_diagonal_response_energy_hz2_s"]) / local_off
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
        "reference_guards_pass": bool(
            local["guards_pass"] and zero["guards_pass"]
        ),
        "guard_errors": list(candidate["guard_errors"]),
        "passed": passed,
        "local_differential_energy": local_diff,
        "local_probe_off_diagonal_energy": local_off,
        "zero_differential_energy": float(
            zero["disturbance"]["mean_differential_frequency_energy_hz2_s"]
        ),
        "record_count": len(records),
    }


def _anchor_verdict(
    differential_ratio: float, probe_cross_ratio: float
) -> dict[str, Any]:
    deviations = {
        "r_d": abs(float(differential_ratio) - BASE_ANCHOR["r_d"])
        / abs(BASE_ANCHOR["r_d"]),
        "r_cross": abs(float(probe_cross_ratio) - BASE_ANCHOR["r_cross"])
        / abs(BASE_ANCHOR["r_cross"]),
    }
    return {
        "deviations": deviations,
        "verdict": (
            "BASE-ANCHOR-REPRODUCED"
            if all(
                value <= BASE_ANCHOR_TOLERANCE_RELATIVE
                for value in deviations.values()
            )
            else "BASE-ANCHOR-DRIFT"
        ),
    }


def classify() -> str:
    _assert_wsl_scratch()
    load_seal()
    rows = {}
    for variant in TOPOLOGY_VARIANTS:
        variant_id = str(variant["variant_id"])
        gate = _read_hashed_json(OUT / variant_id / "eig_gate.json")
        bank = _read_hashed_json(OUT / variant_id / "records.json")
        contract = build_variant_contract(variant)
        summary = _variant_summary(bank["records"], contract)
        rows[variant_id] = {
            "variant": dict(variant),
            "eig_gate": gate,
            "summary": summary,
        }
    nominal = rows["nominal"]
    anchor = _anchor_verdict(
        float(nominal["summary"]["differential_ratio"]),
        float(nominal["summary"]["probe_cross_ratio"]),
    )
    eig_passing = [
        variant_id
        for variant_id, row in rows.items()
        if bool(row["eig_gate"]["passed"])
    ]
    endpoint_passing = [
        variant_id
        for variant_id, row in rows.items()
        if bool(row["summary"]["passed"])
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
        "base_anchor": BASE_ANCHOR,
        "base_anchor_deviations": anchor["deviations"],
        "base_anchor_verdict": anchor["verdict"],
        "variants": rows,
        "eig_passing_variants": eig_passing,
        "endpoint_passing_variants": endpoint_passing,
        "eig_pass_count": len(eig_passing),
        "endpoint_pass_count": len(endpoint_passing),
        "variant_count": len(TOPOLOGY_VARIANTS),
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
        "variant_count": len(TOPOLOGY_VARIANTS),
    }
    _write_new_json(OUT / "formal_manifest.json", manifest_payload)
    return digest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "inventory",
            "measure-capacity",
            "rehearse",
            "prepare",
            "shards",
            "shard",
            "classify",
        ],
    )
    parser.add_argument("args", nargs=argparse.REMAINDER)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "inventory":
        safe_emit(inventory())
    elif args.command == "measure-capacity":
        safe_emit(f"R412 capacity evidence: {measure_capacity()}")
    elif args.command == "rehearse":
        safe_emit(f"R412 rehearsal artifact: {rehearse()}")
    elif args.command == "prepare":
        safe_emit(f"R412 formal seal: {prepare()}")
    elif args.command == "shards":
        safe_emit(json.dumps(variant_ids(), separators=(",", ":")))
    elif args.command == "shard":
        if not args.args:
            raise SystemExit("shard requires a variant id")
        extra = [item for item in args.args[1:] if item not in ("--resume",)]
        if extra:
            raise SystemExit(f"unexpected shard argument: {extra[0]}")
        resume = "--resume" in args.args
        _evaluate_shard(str(args.args[0]), resume=resume)
        safe_emit(f"R412 shard complete: {args.args[0]}")
    else:
        safe_emit(f"R412 formal analysis: {classify()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
