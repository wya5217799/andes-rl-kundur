"""Sealed WSL runner for R440: energy-port robustness expansion (N-2 outages + controller delay).

Owner-authorized supplementary ring 6 (2026-08-19): the constructive
bandpass K=3.5 result (R408/R409) currently covers 10 single-factor
topology variants (R413) and three unseen condition banks (R415/R417).
This round expands the robustness envelope along two frozen axes:

- N-2 axis: 8 combined-outage variants (two inter-area corridor outages,
  two cross-corridor pairs), each passing the CLM-0665 EIG hard gate
  (TDS.test_ok, exit_code=0, init residuals, finite spectrum,
  positive-real guard); unsound variants are recorded, not judged.
- Delay axis: controller output delayed by 1 step (0.2 s) and 2 steps
  (0.4 s) on the nominal topology.

Every variant/delay runs the three R408/R409 arms (zero_feedback /
local_feasibility_native / bandpass_k3p5) under identical conditions
(8 paired probes + 2 disturbances, seed 42, 0.2 s x 50 steps) with the
frozen R409 thresholds (r_d <= 0.95, r_cross <= 1.10, all R379 guards).

Lifecycle (WSL only, always through the scratch launcher):
  python scripts/andes_scratch.py scripts/run_r440_robustness_expansion.py capacity
  python scripts/andes_scratch.py scripts/run_r440_robustness_expansion.py rehearse
  python scripts/andes_scratch.py scripts/run_r440_robustness_expansion.py prepare
  python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py \
      --runner scripts/run_r440_robustness_expansion.py \
      --shards tmp/andes/r440_shards.json --workers N --round R440
  python scripts/andes_scratch.py scripts/run_r440_robustness_expansion.py aggregate

Formal artifacts are create-only with sha256 sidecars under
results/research_loop/r440_robustness_expansion/.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
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

# Frozen chain: R440 -> R413 (which imports R408/R372).
_spec = importlib.util.spec_from_file_location(
    "_r440_r413_parent", ROOT / "scripts/run_r413_topology_robustness.py"
)
if _spec is None or _spec.loader is None:
    raise RuntimeError("cannot load the frozen R413 parent runner")
r413 = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = r413
_spec.loader.exec_module(r413)

ROUND_ID = "R440"
PLAN = ROOT / "memory/rounds/R440/plan.md"
REHEARSAL = ROOT / "memory/rounds/R440/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R440/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R440/formal_seal.json"
OUT = ROOT / "results/research_loop/r440_robustness_expansion"
R413_OUT = ROOT / "results/research_loop/r413_topology_robustness"

# Frozen N-2 variant bank (2026-08-19): two inter-area corridors (7-8 and
# 8-9) each have two parallel circuits; the frozen pairs target corridor
# double-outage and one cross-corridor combination.  Line_2 stays excluded
# (R305 positive-mode precedent).
N2_VARIANTS: tuple[dict[str, Any], ...] = (
    {"variant_id": "n2_out_Line_4_Line_5", "kind": "outage", "line_idxs": ("Line_4", "Line_5")},
    {"variant_id": "n2_out_Line_4_Line_6", "kind": "outage", "line_idxs": ("Line_4", "Line_6")},
    {"variant_id": "n2_out_Line_5_Line_6", "kind": "outage", "line_idxs": ("Line_5", "Line_6")},
    {"variant_id": "n2_out_Line_7_Line_8", "kind": "outage", "line_idxs": ("Line_7", "Line_8")},
    {"variant_id": "n2_out_Line_4_Line_7", "kind": "outage", "line_idxs": ("Line_4", "Line_7")},
    {"variant_id": "n2_out_Line_5_Line_8", "kind": "outage", "line_idxs": ("Line_5", "Line_8")},
    {"variant_id": "n2_out_Line_4_Line_8", "kind": "outage", "line_idxs": ("Line_4", "Line_8")},
    {"variant_id": "n2_out_Line_5_Line_7", "kind": "outage", "line_idxs": ("Line_5", "Line_7")},
)

# Delay axis: nominal topology with controller-output delay (frozen).
DELAY_STEPS = (1, 2)

DIFFERENTIAL_RATIO_MAX = 0.95
PROBE_CROSS_RATIO_MAX = 1.10
STRICT_CROSS_RATIO_MAX = 0.95
BASE_ANCHOR = {"r_d": 0.938947, "r_cross": 0.539791}
BASE_ANCHOR_TOLERANCE_RELATIVE = 1.0e-6

CAPACITY_RUNGS = (1, 2, 4, 8, 12, 16)
CAPACITY_TASKS_PER_RUNG = 32


def safe_emit(message: str, *, stream: TextIO | None = None) -> bool:
    target = sys.stdout if stream is None else stream
    try:
        print(message, file=target, flush=True)
        return True
    except BrokenPipeError:
        return False


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
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
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


def build_contract() -> dict[str, Any]:
    contract = r413.build_variant_contract(r413.variant_by_id("nominal"))
    contract["round"] = ROUND_ID
    contract["r440"] = {
        "n2_variants": [
            {"variant_id": v["variant_id"], "line_idxs": list(v["line_idxs"])}
            for v in N2_VARIANTS
        ],
        "delay_steps": list(DELAY_STEPS),
        "thresholds": {
            "differential_ratio_max": DIFFERENTIAL_RATIO_MAX,
            "probe_cross_ratio_max": PROBE_CROSS_RATIO_MAX,
            "strict_cross_ratio_max": STRICT_CROSS_RATIO_MAX,
            "base_anchor": BASE_ANCHOR,
        },
        "plan_sha256": _sha256_file(PLAN),
    }
    return contract


def contract_sha256(contract: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(contract, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("R440 physical commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R440 must run through scripts/andes_scratch.py")


def authority_checks() -> dict[str, bool]:
    plan_text = PLAN.read_text(encoding="utf-8")
    contract = build_contract()
    return {
        "active_plan": "state: active" in plan_text and "R440" in plan_text,
        "contract_closed": (
            len(contract["r440"]["n2_variants"]) == len(N2_VARIANTS)
            and list(contract["r440"]["delay_steps"]) == list(DELAY_STEPS)
        ),
        "output_absence": not OUT.exists(),
    }


def _build_env_variant(n2_variant: Mapping[str, Any], *, seed: int, steps: int) -> Any:
    """N-2 variant env: two outages applied at system build (R413 pattern)."""
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.evaluation.topology_status import apply_line_outage

    class _N2VariantEnv(AndesMultiVSGEnvV4):
        def _build_system(self):
            ss = super()._build_system()
            for line_idx in n2_variant["line_idxs"]:
                apply_line_outage(ss, str(line_idx))
            return ss

    env = _N2VariantEnv(
        random_disturbance=False,
        comm_fail_prob=0.0,
        comm_delay_steps=0,
    )
    env.seed(int(seed))
    env.STEPS_PER_EPISODE = int(steps)
    return env


def _run_job(
    job: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    n2_variant: Mapping[str, Any] | None = None,
    delay_steps: int = 0,
) -> dict[str, Any]:
    """R413-faithful record loop with optional N-2 variant and delay seam."""
    from andes_rl_kundur.env.andes.vsg_energy_port_env import AndesVSGEnergyPortEnv

    if n2_variant is not None:
        base_env = _build_env_variant(
            n2_variant, seed=int(contract["seed"]), steps=int(contract["steps"])
        )
    else:
        base_env = r413._build_env(
            r413.variant_by_id("nominal"),
            seed=int(contract["seed"]),
            steps=int(contract["steps"]),
        )
    port_env = AndesVSGEnergyPortEnv(base_env=base_env)
    action_map = r413.FeasibilityNativeVSGActionMap(r413.r272_frozen_bess_contract())
    controller = r413._make_controller(str(job["arm_id"]), contract)
    rows: list[dict[str, Any]] = []
    identity: dict[str, Any] = {}
    failure: str | None = None
    previous_power_system_pu = np.zeros(4, dtype=float)
    current_soc = np.full(4, float(contract["soc_initial"]), dtype=float)
    # Delay seam: a FIFO of controller outputs; during the warm-up steps the
    # controller command is zero (no command yet), matching an actuation
    # latency of `delay_steps * 0.2 s`.
    delay_queue: list[np.ndarray] = []
    try:
        port_env.reset(delta_u=dict(job["delta_u"]))
        identity = r413._identity(base_env)
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
            if delay_steps > 0:
                delay_queue.append(np.asarray(controller_action, dtype=float))
                controller_action = (
                    delay_queue.pop(0) if len(delay_queue) > delay_steps
                    else np.zeros(4, dtype=float)
                )
            normalized = controller_action.copy()
            if job["experiment_kind"] == "probe":
                normalized = normalized + r413.probe_request(
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
            row = r413._port_row(info, step_index=_step_index, done=bool(done))
            row = r413._enrich_row(
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
    except Exception as exc:  # noqa: BLE001
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


def _eig_gate_n2(n2_variant: Mapping[str, Any]) -> dict[str, Any]:
    """CLM-0665 hard gate on the N-2 variant's base equilibrium.

    Mirrors R413's eig_gate exactly (PFlow converged -> readback -> TDS
    init -> EIG run -> guard), with every step captured as a recorded
    outcome; any exception is stored in ``failure`` with the gate verdict
    left False (scientific outcome, never a crash).
    """
    contract = build_contract()
    from andes_rl_kundur.evaluation.topology_status import eig_validity_guard

    env = None
    payload: dict[str, Any] = {
        "variant_id": str(n2_variant["variant_id"]),
        "line_idxs": list(n2_variant["line_idxs"]),
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
        "positive_real_tolerance": 1.0e-7,
        "positive_real_count": None,
        "max_real": None,
        "spectrum_pass": False,
        "eigenvalue_count": 0,
    }
    try:
        env = _build_env_variant(
            n2_variant, seed=int(contract["seed"]), steps=int(contract["steps"])
        )
        env.reset(delta_u=None)
        payload["pflow_converged"] = bool(
            getattr(env.ss.PFlow, "converged", False)
        )
        payload["tds_init_return"] = r413._json_safe(env.ss.TDS.init())
        payload["eig_return"] = r413._json_safe(env.ss.EIG.run())
        guard = eig_validity_guard(
            env.ss, positive_real_tolerance=1.0e-7
        )
        payload.update(r413._json_safe(guard))
        payload["eigenvalue_count"] = int(np.asarray(env.ss.EIG.mu).size)
    except Exception as exc:  # noqa: BLE001
        payload["failure"] = f"{type(exc).__name__}: {exc}"
    finally:
        if env is not None:
            try:
                env.close()
            except Exception:
                pass
    return payload


def _block_jobs(arm_id: str, contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    """8 paired probes + 2 disturbances for one arm (R408 block shape)."""
    jobs = []
    probe_condition = {
        "condition_id": "dev3_probe_bus15_minus_0p45",
        "delta_u": {"PQ_Bus15": -0.45},
    }
    for input_mode in contract["mode_ids"]:
        for sign in ("positive", "negative"):
            jobs.append(
                {
                    "order": len(jobs),
                    "phase": "evaluation",
                    "arm_id": arm_id,
                    "experiment_kind": "probe",
                    "condition_id": probe_condition["condition_id"],
                    "delta_u": dict(probe_condition["delta_u"]),
                    "input_mode": input_mode,
                    "sign": sign,
                }
            )
    for condition in (
        {
            "condition_id": "dev3_disturbance_pq1_plus_0p65",
            "delta_u": {"PQ_1": 0.65},
        },
        {
            "condition_id": "dev3_disturbance_bus14_minus_0p55",
            "delta_u": {"PQ_Bus14": -0.55},
        },
    ):
        jobs.append(
            {
                "order": len(jobs),
                "phase": "evaluation",
                "arm_id": arm_id,
                "experiment_kind": "disturbance",
                "condition_id": condition["condition_id"],
                "delta_u": dict(condition["delta_u"]),
                "input_mode": None,
                "sign": None,
            }
        )
    return jobs


def _summarize_block(
    records: list[dict[str, Any]],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    phase = r413.summarize_phase_records(
        list(records), phase="development", contract=contract
    )
    return phase["arm_summaries"]


def _run_scenario_shard(shard_id: str) -> str:
    """One shard = one (variant | delay) block, all three arms."""
    contract = build_contract()
    if shard_id.startswith("n2_"):
        n2_variant = next(
            v for v in N2_VARIANTS if v["variant_id"] == shard_id
        )
        eig = _eig_gate_n2(n2_variant)
        results: dict[str, Any] = {"eig_gate": eig}
        if eig["passed"]:
            all_records = [
                _run_job(job, contract=contract, n2_variant=n2_variant)
                for arm_id in ("zero_feedback", "local_feasibility_native", "bandpass_k3p5")
                for job in _block_jobs(arm_id, contract)
            ]
            summaries = _summarize_block(all_records, contract)
            for arm_id in ("zero_feedback", "local_feasibility_native", "bandpass_k3p5"):
                results[arm_id] = summaries[arm_id]
        return _write_new_json(OUT / "n2" / f"{shard_id}.json", results)
    if shard_id.startswith("delay"):
        delay_steps = int(shard_id.split("_")[1])
        results: dict[str, Any] = {"delay_steps": delay_steps}
        all_records = [
            _run_job(job, contract=contract, delay_steps=delay_steps)
            for arm_id in ("zero_feedback", "local_feasibility_native", "bandpass_k3p5")
            for job in _block_jobs(arm_id, contract)
        ]
        summaries = _summarize_block(all_records, contract)
        for arm_id in ("zero_feedback", "local_feasibility_native", "bandpass_k3p5"):
            results[arm_id] = summaries[arm_id]
        return _write_new_json(OUT / "delay" / f"delay_{delay_steps}.json", results)
    raise SystemExit(f"unknown shard id: {shard_id}")


def _ratio_from_summaries(
    candidate: Mapping[str, Any],
    local: Mapping[str, Any],
) -> dict[str, Any]:
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
    return {
        "r_d": diff_ratio,
        "r_cross": cross_ratio,
        "strict_cross_pass": bool(cross_ratio <= STRICT_CROSS_RATIO_MAX),
        "guards_pass": bool(candidate["guards_pass"]),
        "guard_errors": list(candidate["guard_errors"]),
    }


def _aggregate() -> str:
    """Collect all shards, apply thresholds, produce the final analysis."""
    n2_dir = OUT / "n2"
    delay_dir = OUT / "delay"
    per_n2: dict[str, Any] = {}
    for path in sorted(n2_dir.glob("*.json")):
        entry = _read_hashed_json(path)
        eig = entry["eig_gate"]
        variant_id = str(eig["variant_id"])
        if not eig["passed"]:
            per_n2[variant_id] = {"sound": False, "failure": eig.get("failure")}
            continue
        local = entry["local_feasibility_native"]
        bandpass = entry["bandpass_k3p5"]
        ratios = _ratio_from_summaries(bandpass, local)
        per_n2[variant_id] = {
            "sound": True,
            "passed": bool(
                ratios["r_d"] <= DIFFERENTIAL_RATIO_MAX
                and ratios["r_cross"] <= PROBE_CROSS_RATIO_MAX
                and ratios["guards_pass"]
            ),
            "ratios": ratios,
        }
    per_delay: dict[str, Any] = {}
    for path in sorted(delay_dir.glob("*.json")):
        entry = _read_hashed_json(path)
        delay_steps = int(entry["delay_steps"])
        local = entry["local_feasibility_native"]
        bandpass = entry["bandpass_k3p5"]
        ratios = _ratio_from_summaries(bandpass, local)
        per_delay[str(delay_steps)] = {
            "passed": bool(
                ratios["r_d"] <= DIFFERENTIAL_RATIO_MAX
                and ratios["r_cross"] <= PROBE_CROSS_RATIO_MAX
                and ratios["guards_pass"]
            ),
            "ratios": ratios,
        }
    sound_n2 = [v for v, e in per_n2.items() if e.get("sound")]
    failed = [
        v for v, e in per_n2.items() if e.get("sound") and not e.get("passed")
    ] + [
        str(k) for k, e in per_delay.items() if not e.get("passed")
    ]
    verdict = "ROBUSTNESS-EXPANDED" if not failed else "BOUNDED-FAILURE"
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "contract_sha256": contract_sha256(build_contract()),
        "seal_sha256": _sha256_file(SEAL),
        "classification": {
            "verdict": verdict,
            "sound_n2_count": len(sound_n2),
            "failed_units": failed,
            "per_n2": per_n2,
            "per_delay": per_delay,
        },
    }
    return _write_new_json(OUT / "formal_analysis.json", payload)


def _capacity_job(_job_id: int) -> dict[str, Any]:
    contract = build_contract()
    job = _block_jobs("bandpass_k3p5", contract)[0]
    record = _run_job(job, contract=contract)
    return {"ok": bool(record.get("completed_steps", 0) > 0)}


def measure_capacity() -> str:
    payload = {"rungs": []}
    for workers in CAPACITY_RUNGS:
        start = time.monotonic()
        with ProcessPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(_capacity_job, range(workers * 4)))
        wall = time.monotonic() - start
        payload["rungs"].append(
            {
                "workers": workers,
                "jobs": len(results),
                "wall_seconds": round(wall, 3),
                "throughput_jobs_per_second": round(
                    len(results) / max(wall, 1e-9), 4
                ),
                "all_ok": all(r["ok"] for r in results),
            }
        )
    return json.dumps(payload, indent=2, sort_keys=True)


def rehearse() -> str:
    contract = build_contract()
    checks = {
        "authority": authority_checks(),
        "contract_sha256": contract_sha256(contract),
        "output_absence": not OUT.exists(),
    }
    # one nominal delay-1 trajectory + one N-2 EIG gate
    job = _block_jobs("bandpass_k3p5", contract)[0]
    record = _run_job(job, contract=contract, delay_steps=1)
    checks["delay_reference"] = {
        "rows": int(record.get("completed_steps", 0)),
        "tds_failed": bool(record.get("tds_failed")),
    }
    eig = _eig_gate_n2(N2_VARIANTS[0])
    checks["n2_eig_reference"] = {
        "variant": eig["variant_id"],
        "passed": bool(eig["passed"]),
        "pflow_converged": bool(eig.get("pflow_converged", False)),
        "failure": eig.get("failure"),
    }
    return json.dumps(checks, indent=2, sort_keys=True)


def prepare(other_reserved: int = 0) -> str:
    checks = authority_checks()
    if not all(checks.values()):
        raise RuntimeError(f"authority checks failed: {checks}")
    rehearsal = _read_hashed_json(REHEARSAL)
    if not rehearsal.get("delay_reference", {}).get("rows", 0) > 0:
        raise RuntimeError("rehearsal delay reference failed")
    capacity = _read_hashed_json(CAPACITY)
    selected = int(capacity.get("selected_workers", 0))
    if selected <= 0:
        raise RuntimeError("capacity evidence has no selected rung")
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(build_contract()),
        "plan_sha256": _sha256_file(PLAN),
        "authority": checks,
        "launch": {
            "wsl_python_processes": selected + 1,
            "other_reserved_processes": other_reserved,
            "host_process_budget": selected + 1,
            "native_threads_per_process": 1,
        },
        "sources": {
            "runner": {
                "path": _relative(Path(__file__).resolve()),
                "sha256": _sha256_file(Path(__file__).resolve()),
            },
            "r413_runner": {
                "path": _relative(ROOT / "scripts/run_r413_topology_robustness.py"),
                "sha256": _sha256_file(
                    ROOT / "scripts/run_r413_topology_robustness.py"
                ),
            },
        },
        "formal_authority": True,
        "training_executed": False,
    }
    digest = _write_new_json(SEAL, seal)
    return json.dumps({"seal_sha256": digest}, indent=2, sort_keys=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["capacity", "rehearse", "prepare", "shard", "aggregate"],
    )
    parser.add_argument("shard_id", nargs="?")
    parser.add_argument("--other-reserved", type=int, default=0)
    args = parser.parse_args()
    if args.command == "capacity":
        payload = json.loads(measure_capacity())
        CAPACITY.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        safe_emit(json.dumps(payload, indent=2, sort_keys=True))
    elif args.command == "rehearse":
        payload = json.loads(rehearse())
        _write_new_json(REHEARSAL, payload)
        safe_emit(json.dumps(payload, indent=2, sort_keys=True))
    elif args.command == "prepare":
        safe_emit(prepare(args.other_reserved))
    elif args.command == "shard":
        if args.shard_id is None:
            raise SystemExit("shard requires a shard id")
        safe_emit("R440 shard: " + _run_scenario_shard(args.shard_id))
    else:
        safe_emit(_aggregate())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
