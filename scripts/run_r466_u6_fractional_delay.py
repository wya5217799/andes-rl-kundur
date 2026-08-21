"""R466 U6 exact fractional command-delay margins (WSL-only adapter)."""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import hashlib
import json
import multiprocessing as mp
import os
import platform
import sys
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"
os.environ["DISABLE_TOGGLER"] = "1"

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import numpy as np  # noqa: E402
import run_r440_robustness_expansion as r440  # noqa: E402
import scipy  # noqa: E402
import scipy.linalg as la  # noqa: E402

from andes_rl_kundur.evaluation import u6_fractional_delay as u6  # noqa: E402

ROUND = "R466"
PLAN = ROOT / "memory/rounds/R466/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
CAPACITY = ROOT / "memory/rounds/R466/capacity_evidence.json"
REHEARSAL = ROOT / "memory/rounds/R466/rehearsal.json"
SEAL = ROOT / "memory/rounds/R466/formal_seal.json"
OUT = ROOT / "results/research_loop/r466_u6_fractional_delay"
R459 = ROOT / "results/research_loop/r459_u1_u8_shared_export"
R450 = ROOT / "results/research_loop/r450_p2_delay_loop/formal_analysis.json"
WORKERS = 15
ARMS = ("zero_feedback", "local_feasibility_native", "bandpass_k3p5")
THRESHOLD = 0.95


def _utc() -> str:
    return datetime.now(UTC).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


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
    if isinstance(value, (np.complexfloating, complex)):
        return {"real": float(np.real(value)), "imag": float(np.imag(value))}
    return value


def _json_new(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or Path(f"{path}.sha256").exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(_json_safe(payload), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    digest = _sha256(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def _npz_new(path: Path, **arrays: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or Path(f"{path}.sha256").exists():
        raise FileExistsError(path)
    np.savez_compressed(path, **arrays)
    digest = _sha256(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def _text_new(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or Path(f"{path}.sha256").exists():
        raise FileExistsError(path)
    path.write_text(text, encoding="utf-8", newline="\n")
    digest = _sha256(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def _authority(absent: bool) -> dict[str, bool]:
    plan = PLAN.read_text(encoding="utf-8")
    checks = {
        "active_plan": "round: R466" in plan and "state: active" in plan,
        "active_line": "line_id: yang-md-decoupling-marl" in LINE.read_text(encoding="utf-8"),
        "r459_verified": (R459 / "checks/verification_report.json").is_file(),
        "r450_hashed": R450.is_file() and Path(f"{R450}.sha256").is_file(),
        "linux_runtime": platform.system() == "Linux",
        "one_native_thread_default": all(os.environ.get(name) == "1" for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")),
    }
    if absent:
        checks["formal_output_absent"] = not OUT.exists()
    return checks


def _sources() -> dict[str, dict[str, str]]:
    paths = {
        "runner": Path(__file__).resolve(),
        "implementation": ROOT / "src/andes_rl_kundur/evaluation/u6_fractional_delay.py",
        "plan": PLAN,
        "r459_verification": R459 / "checks/verification_report.json",
        "r459_continuous": R459 / "model_exports/object_b/continuous_reduced_model.npz",
        "r459_sampled": R459 / "model_exports/object_b/sampled_model.npz",
        "r459_headroom": R459 / "model_exports/object_b/headroom_modes.json",
        "r450_parent": R450,
        "r440_runner": ROOT / "scripts/run_r440_robustness_expansion.py",
    }
    return {name: {"path": _relative(path), "sha256": _sha256(path)} for name, path in paths.items()}


def _linear_model() -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    continuous = np.load(R459 / "model_exports/object_b/continuous_reduced_model.npz")
    sampled = np.load(R459 / "model_exports/object_b/sampled_model.npz")
    headroom = np.asarray(json.loads((R459 / "model_exports/object_b/headroom_modes.json").read_text(encoding="utf-8"))["upper_system_pu"], dtype=float)
    a_post = sampled["A_post_step"]
    c_post = sampled["C_post_step"]
    values, vectors = la.eig(a_post)
    gauge_index = int(np.argmin(np.abs(values - 1.0)))
    gauge = np.real(vectors[:, gauge_index])
    gauge /= np.linalg.norm(gauge)
    complement = la.null_space(gauge.reshape(1, -1))
    a_c = complement.T @ continuous["A_continuous"] @ complement
    b_c = complement.T @ continuous["B_continuous"][:, :4] @ np.diag(headroom)
    c = continuous["C_frequency_continuous"] @ complement
    checks = {
        "gauge_eigenvalue_real": float(np.real(values[gauge_index])),
        "gauge_eigenvalue_imag": float(np.imag(values[gauge_index])),
        "sampled_gauge_residual": float(np.linalg.norm(a_post @ gauge - values[gauge_index] * gauge)),
        "sampled_gauge_output_norm": float(np.linalg.norm(c_post @ gauge)),
        "continuous_gauge_to_quotient_leakage": float(np.linalg.norm(complement.T @ continuous["A_continuous"] @ gauge)),
        "complement_shape": list(complement.shape),
        "headroom_system_pu": headroom.tolist(),
    }
    return a_c, b_c, c, {"checks": checks, "complement": complement}


def _endpoint_checks(a_c: np.ndarray, b_c: np.ndarray, c: np.ndarray) -> dict[str, Any]:
    a0, m0 = u6.augmented_matrix(a_c, b_c, c, 0.0)
    a1, m1 = u6.augmented_matrix(a_c, b_c, c, u6.TS)
    a1_left, m1_left = u6.augmented_matrix(a_c, b_c, c, u6.TS - 1e-9)
    a2, _ = u6.augmented_matrix(a_c, b_c, c, 2.0)
    ad, b0, b1 = u6.delay_split(a_c, b_c, 0.0)
    return {
        "dimension": int(a0.shape[0]),
        "tau_zero_delta": m0["fractional_delta_s"],
        "tau_zero_B0_equals_Bd_max_abs": float(np.max(np.abs(b0 - u6._zoh_input(a_c, b_c, u6.TS)))),
        "tau_zero_B1_max_abs": float(np.max(np.abs(b1))),
        "tau_zero_Ad_identity_max_abs": float(np.max(np.abs(ad - la.expm(a_c * u6.TS)))),
        "left_limit_to_next_integer_max_abs": float(np.max(np.abs(a1_left - a1))),
        "left_limit_B0_max_abs": float(np.max(np.abs(m1_left["B0"]))),
        "left_limit_B1_to_Bd_max_abs": float(np.max(np.abs(m1_left["B1"] - u6._zoh_input(a_c, b_c, u6.TS)))),
        "tau_two_finite": bool(np.all(np.isfinite(a2))),
    }


def _mode_hash(base_env: Any) -> str:
    values = np.ascontiguousarray(np.asarray(base_env.ss.dae.z, dtype=float))
    return hashlib.sha256(values.tobytes()).hexdigest()


def _run_fractional_job(job: Mapping[str, Any], contract: Mapping[str, Any], tau: float) -> dict[str, Any]:
    """Advance two literal TDS segments while evaluating control once per sample."""
    from andes_rl_kundur.env.andes.vsg_energy_port_env import AndesVSGEnergyPortEnv

    base_env = r440.r413._build_env(
        r440.r413.variant_by_id("nominal"), seed=int(contract["seed"]), steps=2 * int(contract["steps"])
    )
    port_env = AndesVSGEnergyPortEnv(base_env=base_env)
    action_map = r440.r413.FeasibilityNativeVSGActionMap(r440.r413.r272_frozen_bess_contract())
    controller = r440.r413._make_controller(str(job["arm_id"]), contract)
    rows: list[dict[str, Any]] = []
    identity: dict[str, Any] = {}
    failure: str | None = None
    previous_power = np.zeros(4, dtype=float)
    previous_controller = np.zeros(4, dtype=float)
    current_soc = np.full(4, float(contract["soc_initial"]), dtype=float)
    all_mode_hashes: list[str] = []
    try:
        port_env.reset(delta_u=dict(job["delta_u"]))
        identity = r440.r413._identity(base_env)
        for step_index in range(int(contract["steps"])):
            frequencies = np.asarray(base_env._get_vsg_omega(), dtype=float) * float(contract["nominal_frequency_hz"])
            current_controller = np.zeros(4, dtype=float) if controller is None else np.asarray(
                controller.act(frequencies_hz=frequencies, dt_seconds=float(contract["dt_seconds"])), dtype=float
            )
            probe = np.zeros(4, dtype=float)
            if job["experiment_kind"] == "probe":
                probe = r440.r413.probe_request(str(job["input_mode"]), str(job["sign"]), contract=contract)
            segment_rows = []
            last = None
            for segment_index, (duration, delayed_controller) in enumerate(
                ((tau, previous_controller), (u6.TS - tau, current_controller))
            ):
                if duration <= 1e-12:
                    continue
                normalized = delayed_controller + probe
                common = np.mean(normalized) * np.ones(4)
                differential = normalized - common
                voltage = np.asarray([base_env.ss.GENCLS.v.v[position] for position in base_env._vsg_pos], dtype=float)
                mapped = action_map.map_action(
                    normalized_actions=normalized, previous_power_system_pu=previous_power,
                    soc=current_soc, voltage_pu=voltage, dt_seconds=float(duration),
                )
                base_env.DT = float(duration)
                _obs, _reward, done, info = port_env.step(mapped.feasible_power_system_pu)
                raw = r440.r413._port_row(info, step_index=step_index, done=bool(done))
                raw = r440.r413._enrich_row(
                    raw, normalized=normalized, controller_action=delayed_controller,
                    common_action=common, differential_action=differential, mapped=mapped,
                )
                mode = _mode_hash(base_env)
                all_mode_hashes.append(mode)
                segment_rows.append({
                    "segment_index": segment_index, "duration_seconds": float(duration),
                    "controller_output_used": delayed_controller.tolist(), "probe_request": probe.tolist(),
                    "mode_hash": mode, "row": raw,
                })
                previous_power = np.asarray(raw["commanded_power_system_pu"], dtype=float)
                current_soc = np.asarray(raw["soc"], dtype=float)
                last = (raw, mapped, normalized, delayed_controller, common, differential)
                if raw["tds_failed"]:
                    failure = "TDS failed"
                    break
            if last is None:
                raise RuntimeError("fractional split produced no positive-duration segment")
            raw, mapped, normalized, delayed_controller, common, differential = last
            raw["fractional_transport"] = {
                "tau_seconds": float(tau), "controller_sample_seconds": u6.TS,
                "controller_evaluated_once": True, "previous_controller_output": previous_controller.tolist(),
                "current_controller_output": current_controller.tolist(), "segments": segment_rows,
            }
            rows.append(raw)
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


def _all_jobs(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [job for arm in ARMS for job in r440._block_jobs(arm, contract)]


def _point(records: list[dict[str, Any]], contract: Mapping[str, Any], tau: float) -> dict[str, Any]:
    invalid = [record for record in records if record["tds_failed"] or record["completed_steps"] != int(contract["steps"])]
    mode_discontinuity = any(record["mode_discontinuity"] for record in records)
    summaries = r440._summarize_block(records, contract)
    ratios = r440._ratio_from_summaries(summaries["bandpass_k3p5"], summaries["local_feasibility_native"])
    return {
        "tau_seconds": float(tau), "record_count": len(records), "invalid_count": len(invalid),
        "mode_discontinuity": mode_discontinuity, "ratios": ratios,
        "summaries": summaries,
    }


def _run_point(pool: futures.ProcessPoolExecutor, contract: Mapping[str, Any], tau: float) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    jobs = _all_jobs(contract)
    records = list(pool.map(_run_fractional_job, jobs, [contract] * len(jobs), [tau] * len(jobs)))
    return _point(records, contract, tau), records


def rehearse() -> None:
    if REHEARSAL.exists() or CAPACITY.exists():
        raise FileExistsError("R466 rehearsal/capacity exists")
    authority = _authority(True)
    if not all(authority.values()):
        raise RuntimeError(authority)
    start = time.perf_counter()
    a_c, b_c, c, model = _linear_model()
    endpoints = _endpoint_checks(a_c, b_c, c)
    spectra = {}
    for tau in (0.0, 0.1, 0.2):
        matrix, _ = u6.augmented_matrix(a_c, b_c, c, tau)
        spec = u6.spectrum(matrix)
        spectra[str(tau)] = {"max_modulus": float(np.max(np.abs(spec.values))), "max_residual": float(np.max(spec.residuals))}
    contract = r440.build_contract()
    record = _run_fractional_job(r440._block_jobs("bandpass_k3p5", contract)[0], contract, 0.1)
    segment_lengths = [row["duration_seconds"] for row in record["steps"][0]["fractional_transport"]["segments"]] if record["steps"] else []
    checks = {
        "authority": authority, "model": model["checks"], "endpoints": endpoints,
        "spectra": spectra, "representative_completed_steps": record["completed_steps"],
        "representative_tds_failed": record["tds_failed"], "representative_mode_discontinuity": record["mode_discontinuity"],
        "first_outer_segment_lengths": segment_lengths,
    }
    passed = bool(
        endpoints["dimension"] == 149 and endpoints["tau_zero_B0_equals_Bd_max_abs"] <= 1e-12
        and endpoints["tau_zero_B1_max_abs"] <= 1e-12 and endpoints["left_limit_to_next_integer_max_abs"] <= 1e-8
        and max(row["max_residual"] for row in spectra.values()) <= 1e-9
        and record["completed_steps"] == int(contract["steps"]) and not record["tds_failed"]
        and np.allclose(segment_lengths, [0.1, 0.1], atol=1e-12, rtol=0.0)
    )
    checks["passed"] = passed
    if not passed:
        raise RuntimeError(checks)
    wall = time.perf_counter() - start
    _json_new(REHEARSAL, {"round": ROUND, "created_utc": _utc(), "checks": checks, "wall_seconds": wall})
    available = None
    try:
        lines = Path("/proc/meminfo").read_text(encoding="utf-8").splitlines()
        available = int(next(line.split()[1] for line in lines if line.startswith("MemAvailable:"))) * 1024
    except (OSError, StopIteration, ValueError):
        pass
    _json_new(CAPACITY, {
        "round": ROUND, "created_utc": _utc(), "readiness": "RUN-READY",
        "capacity_anchor": "R459 selected four native threads for serial small dense linear algebra; R460 measured 15 physical workers plus one orchestrator 50.96% faster than eight workers",
        "pole_scan_processes": 1, "pole_scan_native_threads": 4,
        "nonlinear_unique_jobs_max": 90, "nonlinear_workers": WORKERS, "orchestrator_processes": 1,
        "wsl_python_processes_nonlinear": WORKERS + 1, "host_process_budget": 17,
        "native_threads_per_nonlinear_process": 1, "other_reserved_processes": 0,
        "wsl_available_memory_bytes": available, "gpu_selected": False,
        "gpu_reason": "149-by-149 dense eigenproblems and ANDES TDS are CPU-bound; no measured GPU path",
        "rehearsal_wall_seconds": wall,
    })
    print(json.dumps(_json_safe(checks), indent=2))


def prepare() -> None:
    if SEAL.exists() or OUT.exists():
        raise FileExistsError("R466 seal/output exists")
    authority = _authority(True)
    if not all(authority.values()):
        raise RuntimeError(authority)
    payload = {
        "round": ROUND, "created_utc": _utc(), "authority": authority, "sources": _sources(),
        "rehearsal_sha256": _sha256(REHEARSAL), "capacity_sha256": _sha256(CAPACITY),
        "formal_output": _relative(OUT), "scan_taus_seconds": u6.SCAN_TAUS.tolist(),
        "nonlinear_initial_bracket_seconds": [0.0, 0.2], "nonlinear_new_midpoints_max": 3,
        "nonlinear_unique_jobs_max": 90, "workers": WORKERS, "retry_policy": "none",
        "pole_outcomes": ["NOMINAL-LOCAL-CROSSING-VALID", "NO-CROSSING-UP-TO-2S", "NEAR-DEFECTIVE-CROSSING", "POLE-TRACKING-INVALID"],
        "nonlinear_outcomes": ["FINITE-BANK-FRACTIONAL-BRACKET", "OBSERVED-EXACT-THRESHOLD", "MODE-BOUNDARY-NO-IVT", "NONLINEAR-FRACTIONAL-INVALID"],
    }
    print(_json_new(SEAL, payload))


def _verify_seal() -> dict[str, Any]:
    seal = json.loads(SEAL.read_text(encoding="utf-8"))
    for name, row in seal["sources"].items():
        if _sha256(ROOT / row["path"]) != row["sha256"]:
            raise RuntimeError(f"source drift: {name}")
    return seal


def _linear_analysis() -> tuple[dict[str, Any], dict[str, Any]]:
    a_c, b_c, c, model = _linear_model()
    try:
        from threadpoolctl import threadpool_limits
        context = threadpool_limits(limits=4)
    except ImportError:
        from contextlib import nullcontext
        context = nullcontext()
    with context:
        result = u6.track_branches(a_c, b_c, c)
    verdict, checks = u6.classify_tracking(result)
    checks["endpoints"] = _endpoint_checks(a_c, b_c, c)
    checks["model"] = model["checks"]
    checks["max_residual"] = float(np.max(result["residuals"]))
    checks["max_inverse_overlap"] = float(np.max(result["conditions"]))
    checks["max_match_cost"] = float(np.max(result["match_costs"]))
    return result, {"verdict": verdict, "checks": checks}


def _nonlinear_analysis() -> tuple[dict[str, Any], dict[float, list[dict[str, Any]]]]:
    parent = r440._read_hashed_json(R450)
    endpoints = {
        0.0: float(parent["nonlinear"]["0"]["ratios"]["r_d"]),
        0.2: float(parent["nonlinear"]["1"]["ratios"]["r_d"]),
    }
    if not endpoints[0.0] < THRESHOLD < endpoints[0.2]:
        raise RuntimeError(f"parent endpoint bracket absent: {endpoints}")
    contract = r440.build_contract()
    lower, upper = 0.0, 0.2
    points: list[dict[str, Any]] = []
    raw: dict[float, list[dict[str, Any]]] = {}
    outcome = "FINITE-BANK-FRACTIONAL-BRACKET"
    context = mp.get_context("spawn")
    with futures.ProcessPoolExecutor(max_workers=WORKERS, mp_context=context) as pool:
        for _level in range(3):
            midpoint = 0.5 * (lower + upper)
            point, records = _run_point(pool, contract, midpoint)
            points.append(point)
            raw[midpoint] = records
            if point["invalid_count"]:
                outcome = "NONLINEAR-FRACTIONAL-INVALID"
                break
            if point["mode_discontinuity"]:
                outcome = "MODE-BOUNDARY-NO-IVT"
                break
            value = float(point["ratios"]["r_d"])
            if value == THRESHOLD:
                lower = upper = midpoint
                outcome = "OBSERVED-EXACT-THRESHOLD"
                break
            if value < THRESHOLD:
                lower = midpoint
            else:
                upper = midpoint
    valid = outcome in ("FINITE-BANK-FRACTIONAL-BRACKET", "OBSERVED-EXACT-THRESHOLD")
    if outcome == "FINITE-BANK-FRACTIONAL-BRACKET" and upper - lower > 0.025 + 1e-12:
        outcome = "NONLINEAR-FRACTIONAL-INVALID"
        valid = False
    return {
        "verdict": outcome, "threshold": THRESHOLD, "parent_endpoints": endpoints,
        "new_points": points, "final_bracket_seconds": [lower, upper],
        "final_bracket_width_seconds": upper - lower, "all_checks_pass": valid,
    }, raw


def run() -> None:
    if OUT.exists():
        raise FileExistsError(OUT)
    seal = _verify_seal()
    start = time.perf_counter()
    linear, linear_report = _linear_analysis()
    nonlinear, raw = _nonlinear_analysis()
    OUT.mkdir(parents=True, exist_ok=False)
    b0 = np.stack([row["B0"] for row in linear["metadata"]])
    b1 = np.stack([row["B1"] for row in linear["metadata"]])
    _npz_new(
        OUT / "linear/all_pole_scan.npz", tau_seconds=linear["taus"], eigenvalues=linear["values"],
        left_eigenvectors=linear["left"], right_eigenvectors=linear["right"], residuals=linear["residuals"],
        inverse_left_right_overlaps=linear["conditions"], match_costs=linear["match_costs"],
        B0=b0, B1=b1, augmented_matrices=np.stack(linear["matrices"]),
    )
    matrix_registry = [{key: value for key, value in row.items() if key not in ("B0", "B1")} for row in linear["metadata"]]
    _json_new(OUT / "linear/matrix_registry.json", matrix_registry)
    branch_lines = []
    for tau_index, tau in enumerate(linear["taus"]):
        for branch in range(linear["values"].shape[1]):
            value = linear["values"][tau_index, branch]
            branch_lines.append(json.dumps({
                "tau_seconds": float(tau), "branch_id": branch, "eigenvalue_real": float(np.real(value)),
                "eigenvalue_imag": float(np.imag(value)), "modulus": float(abs(value)),
                "residual": float(linear["residuals"][tau_index, branch]),
                "inverse_left_right_overlap": float(linear["conditions"][tau_index, branch]),
                "match_cost_from_previous": float(linear["match_costs"][tau_index, branch]),
            }, sort_keys=True))
    _text_new(OUT / "linear/branch_table.jsonl", "\n".join(branch_lines) + "\n")
    _json_new(OUT / "linear/pole_tracking_report.json", linear_report | {"crossing": linear["crossing"]})
    for tau, records in raw.items():
        token = f"tau_{tau:.3f}".replace(".", "p")
        _json_new(OUT / f"nonlinear/{token}/raw_records.json", {"tau_seconds": tau, "records": records})
    _json_new(OUT / "nonlinear/fractional_bisection.json", nonlinear)
    verification = {
        "round": ROUND, "created_utc": _utc(), "pole_verdict": linear_report["verdict"],
        "nonlinear_verdict": nonlinear["verdict"], "formal_seal_sha256": _sha256(SEAL),
        "linear_checks_pass": linear_report["verdict"] != "POLE-TRACKING-INVALID",
        "nonlinear_checks_pass": nonlinear["all_checks_pass"],
        "publication_entry_valid": linear_report["verdict"] != "POLE-TRACKING-INVALID" and nonlinear["all_checks_pass"],
    }
    _json_new(OUT / "checks/verification_report.json", verification)
    _json_new(OUT / "provenance/runtime.json", {
        "wall_seconds": time.perf_counter() - start, "python": sys.version, "platform": platform.platform(),
        "numpy": np.__version__, "scipy": scipy.__version__, "pole_processes": 1, "pole_native_threads": 4,
        "nonlinear_workers": WORKERS, "nonlinear_native_threads_per_process": 1,
        "formal_seal_sha256": _sha256(SEAL), "seal": seal,
    })
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    (OUT / "SHA256SUMS").write_text("".join(f"{_sha256(path)}  {path.relative_to(OUT).as_posix()}\n" for path in files), encoding="utf-8", newline="\n")
    print(json.dumps(_json_safe(verification | {"crossing": linear["crossing"], "final_bracket_seconds": nonlinear["final_bracket_seconds"]}), indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("rehearse", "prepare", "run"))
    args = parser.parse_args()
    {"rehearse": rehearse, "prepare": prepare, "run": run}[args.command]()


if __name__ == "__main__":
    main()
