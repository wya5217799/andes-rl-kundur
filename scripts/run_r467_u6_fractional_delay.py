"""R467 acyclic-telemetry successor for the sealed R466 U6 experiment."""

from __future__ import annotations

import argparse
import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import run_r466_u6_fractional_delay as base

ROOT = Path(__file__).resolve().parents[1]
base.ROUND = "R467"
base.PLAN = ROOT / "memory/rounds/R467/plan.md"
base.CAPACITY = ROOT / "memory/rounds/R467/capacity_evidence.json"
base.REHEARSAL = ROOT / "memory/rounds/R467/rehearsal.json"
base.SEAL = ROOT / "memory/rounds/R467/formal_seal.json"
base.OUT = ROOT / "results/research_loop/r467_u6_fractional_delay"


def _authority(absent: bool) -> dict[str, bool]:
    plan = base.PLAN.read_text(encoding="utf-8")
    checks = {
        "active_plan": "round: R467" in plan and "state: active" in plan,
        "active_line": "line_id: yang-md-decoupling-marl" in base.LINE.read_text(encoding="utf-8"),
        "r459_verified": (base.R459 / "checks/verification_report.json").is_file(),
        "r450_hashed": base.R450.is_file() and Path(f"{base.R450}.sha256").is_file(),
        "r466_preserved": (ROOT / "memory/rounds/R466/formal_seal.json").is_file()
        and (ROOT / "results/research_loop/r466_u6_fractional_delay/linear/all_pole_scan.npz").is_file(),
        "linux_runtime": base.platform.system() == "Linux",
        "one_native_thread_default": all(
            base.os.environ.get(name) == "1"
            for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
        ),
    }
    if absent:
        checks["formal_output_absent"] = not base.OUT.exists()
    return checks


def _sources() -> dict[str, dict[str, str]]:
    paths = {
        "successor_runner": Path(__file__).resolve(),
        "sealed_r466_runner": ROOT / "scripts/run_r466_u6_fractional_delay.py",
        "implementation": ROOT / "src/andes_rl_kundur/evaluation/u6_fractional_delay.py",
        "plan": base.PLAN,
        "r466_seal": ROOT / "memory/rounds/R466/formal_seal.json",
        "r466_partial_linear": ROOT / "results/research_loop/r466_u6_fractional_delay/linear/all_pole_scan.npz",
        "r459_verification": base.R459 / "checks/verification_report.json",
        "r459_continuous": base.R459 / "model_exports/object_b/continuous_reduced_model.npz",
        "r459_sampled": base.R459 / "model_exports/object_b/sampled_model.npz",
        "r459_headroom": base.R459 / "model_exports/object_b/headroom_modes.json",
        "r450_parent": base.R450,
        "r440_runner": ROOT / "scripts/run_r440_robustness_expansion.py",
    }
    return {name: {"path": base._relative(path), "sha256": base._sha256(path)} for name, path in paths.items()}


def _mode_hash(base_env: Any) -> str:
    values = np.ascontiguousarray(np.asarray(base_env.ss.dae.z, dtype=float))
    return hashlib.sha256(values.tobytes()).hexdigest()


def _run_fractional_job(job: Mapping[str, Any], contract: Mapping[str, Any], tau: float) -> dict[str, Any]:
    """R466 physics with an independent, acyclic segment-row snapshot."""
    from andes_rl_kundur.env.andes.vsg_energy_port_env import AndesVSGEnergyPortEnv

    base_env = base.r440.r413._build_env(
        base.r440.r413.variant_by_id("nominal"), seed=int(contract["seed"]), steps=2 * int(contract["steps"])
    )
    port_env = AndesVSGEnergyPortEnv(base_env=base_env)
    action_map = base.r440.r413.FeasibilityNativeVSGActionMap(base.r440.r413.r272_frozen_bess_contract())
    controller = base.r440.r413._make_controller(str(job["arm_id"]), contract)
    rows: list[dict[str, Any]] = []
    identity: dict[str, Any] = {}
    failure: str | None = None
    previous_power = np.zeros(4, dtype=float)
    previous_controller = np.zeros(4, dtype=float)
    current_soc = np.full(4, float(contract["soc_initial"]), dtype=float)
    all_mode_hashes: list[str] = []
    try:
        port_env.reset(delta_u=dict(job["delta_u"]))
        identity = base.r440.r413._identity(base_env)
        for step_index in range(int(contract["steps"])):
            frequencies = np.asarray(base_env._get_vsg_omega(), dtype=float) * float(contract["nominal_frequency_hz"])
            current_controller = np.zeros(4, dtype=float) if controller is None else np.asarray(
                controller.act(frequencies_hz=frequencies, dt_seconds=float(contract["dt_seconds"])), dtype=float
            )
            probe = np.zeros(4, dtype=float)
            if job["experiment_kind"] == "probe":
                probe = base.r440.r413.probe_request(
                    str(job["input_mode"]), str(job["sign"]), contract=contract
                )
            segment_rows = []
            last = None
            for segment_index, (duration, delayed_controller) in enumerate(
                ((tau, previous_controller), (base.u6.TS - tau, current_controller))
            ):
                if duration <= 1e-12:
                    continue
                normalized = delayed_controller + probe
                common = np.mean(normalized) * np.ones(4)
                differential = normalized - common
                voltage = np.asarray(
                    [base_env.ss.GENCLS.v.v[position] for position in base_env._vsg_pos], dtype=float
                )
                mapped = action_map.map_action(
                    normalized_actions=normalized, previous_power_system_pu=previous_power,
                    soc=current_soc, voltage_pu=voltage, dt_seconds=float(duration),
                )
                base_env.DT = float(duration)
                _obs, _reward, done, info = port_env.step(mapped.feasible_power_system_pu)
                raw = base.r440.r413._port_row(info, step_index=step_index, done=bool(done))
                raw = base.r440.r413._enrich_row(
                    raw, normalized=normalized, controller_action=delayed_controller,
                    common_action=common, differential_action=differential, mapped=mapped,
                )
                mode = _mode_hash(base_env)
                all_mode_hashes.append(mode)
                segment_rows.append({
                    "segment_index": segment_index, "duration_seconds": float(duration),
                    "controller_output_used": delayed_controller.tolist(), "probe_request": probe.tolist(),
                    "mode_hash": mode, "row": dict(raw),
                })
                previous_power = np.asarray(raw["commanded_power_system_pu"], dtype=float)
                current_soc = np.asarray(raw["soc"], dtype=float)
                last = raw
                if raw["tds_failed"]:
                    failure = "TDS failed"
                    break
            if last is None:
                raise RuntimeError("fractional split produced no positive-duration segment")
            last["fractional_transport"] = {
                "tau_seconds": float(tau), "controller_sample_seconds": base.u6.TS,
                "controller_evaluated_once": True, "previous_controller_output": previous_controller.tolist(),
                "current_controller_output": current_controller.tolist(), "segments": segment_rows,
            }
            rows.append(last)
            previous_controller = current_controller
            if failure is not None:
                break
    except Exception as exc:  # noqa: BLE001
        failure = f"{type(exc).__name__}: {exc}"
    finally:
        port_env.close()
    return {
        "phase": str(job["phase"]), "arm_id": str(job["arm_id"]),
        "experiment_kind": str(job["experiment_kind"]), "condition_id": str(job["condition_id"]),
        "delta_u": dict(job["delta_u"]), "input_mode": job["input_mode"], "sign": job["sign"],
        "tau_seconds": float(tau), "identity": identity, "steps": rows,
        "completed_steps": len(rows), "tds_failed": failure is not None or any(bool(row["tds_failed"]) for row in rows),
        "failure": failure, "mode_hashes": sorted(set(all_mode_hashes)),
        "mode_discontinuity": len(set(all_mode_hashes)) > 1,
        "reward_used_for_gate": False, "training_executed": False,
    }


def rehearse() -> None:
    if base.REHEARSAL.exists() or base.CAPACITY.exists():
        raise FileExistsError("R467 rehearsal/capacity exists")
    authority = _authority(True)
    if not all(authority.values()):
        raise RuntimeError(authority)
    start = base.time.perf_counter()
    a_c, b_c, c, model = base._linear_model()
    endpoints = base._endpoint_checks(a_c, b_c, c)
    spectra = {}
    for tau in (0.0, 0.1, 0.2):
        matrix, _ = base.u6.augmented_matrix(a_c, b_c, c, tau)
        spec = base.u6.spectrum(matrix)
        spectra[str(tau)] = {
            "max_modulus": float(np.max(np.abs(spec.values))),
            "max_residual": float(np.max(spec.residuals)),
        }
    contract = base.r440.build_contract()
    record = _run_fractional_job(base.r440._block_jobs("bandpass_k3p5", contract)[0], contract, 0.1)
    encoded = base.json.dumps(base._json_safe(record), sort_keys=True, allow_nan=False)
    decoded = base.json.loads(encoded)
    segment_lengths = [
        row["duration_seconds"]
        for row in record["steps"][0]["fractional_transport"]["segments"]
    ] if record["steps"] else []
    checks = {
        "authority": authority, "model": model["checks"], "endpoints": endpoints,
        "spectra": spectra, "representative_completed_steps": record["completed_steps"],
        "representative_tds_failed": record["tds_failed"],
        "representative_mode_discontinuity": record["mode_discontinuity"],
        "first_outer_segment_lengths": segment_lengths,
        "strict_json_bytes": len(encoded.encode("utf-8")),
        "strict_json_roundtrip_steps": len(decoded["steps"]),
    }
    passed = bool(
        endpoints["dimension"] == 149
        and endpoints["tau_zero_B0_equals_Bd_max_abs"] <= 1e-12
        and endpoints["tau_zero_B1_max_abs"] <= 1e-12
        and endpoints["left_limit_to_next_integer_max_abs"] <= 1e-8
        and max(row["max_residual"] for row in spectra.values()) <= 1e-9
        and record["completed_steps"] == int(contract["steps"])
        and len(decoded["steps"]) == int(contract["steps"])
        and not record["tds_failed"]
        and np.allclose(segment_lengths, [0.1, 0.1], atol=1e-12, rtol=0.0)
    )
    checks["passed"] = passed
    if not passed:
        raise RuntimeError(checks)
    wall = base.time.perf_counter() - start
    base._json_new(base.REHEARSAL, {"round": base.ROUND, "created_utc": base._utc(), "checks": checks, "wall_seconds": wall})
    available = None
    try:
        lines = Path("/proc/meminfo").read_text(encoding="utf-8").splitlines()
        available = int(next(line.split()[1] for line in lines if line.startswith("MemAvailable:"))) * 1024
    except (OSError, StopIteration, ValueError):
        pass
    base._json_new(base.CAPACITY, {
        "round": base.ROUND, "created_utc": base._utc(), "readiness": "RUN-READY",
        "capacity_anchor": "R459 four native threads for linear algebra; R460 15 physical workers plus one orchestrator 50.96% faster than eight workers",
        "pole_scan_processes": 1, "pole_scan_native_threads": 4,
        "nonlinear_unique_jobs_max": 90, "nonlinear_workers": base.WORKERS,
        "orchestrator_processes": 1, "wsl_python_processes_nonlinear": base.WORKERS + 1,
        "host_process_budget": 17, "native_threads_per_nonlinear_process": 1,
        "other_reserved_processes": 0, "wsl_available_memory_bytes": available,
        "gpu_selected": False,
        "gpu_reason": "149-by-149 dense eigenproblems and ANDES TDS are CPU-bound; no measured GPU path",
        "rehearsal_wall_seconds": wall,
    })
    print(base.json.dumps(base._json_safe(checks), indent=2))


base._authority = _authority
base._sources = _sources
base._run_fractional_job = _run_fractional_job


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("rehearse", "prepare", "run"))
    args = parser.parse_args()
    {"rehearse": rehearse, "prepare": base.prepare, "run": base.run}[args.command]()


if __name__ == "__main__":
    main()
