"""R465 U5 complete Object-B total sensitivity (WSL-only formal adapter)."""

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
import scipy  # noqa: E402

from andes_rl_kundur.evaluation import u5_total_sensitivity as u5  # noqa: E402

ROUND = "R465"
PLAN = ROOT / "memory/rounds/R465/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
CAPACITY = ROOT / "memory/rounds/R465/capacity_evidence.json"
REHEARSAL = ROOT / "memory/rounds/R465/rehearsal.json"
SEAL = ROOT / "memory/rounds/R465/formal_seal.json"
OUT = ROOT / "results/research_loop/r465_u5_total_sensitivity"
R459 = ROOT / "results/research_loop/r459_u1_u8_shared_export"
R449 = ROOT / "results/research_loop/r449_p1_sensitivity/formal_analysis.json"
WORKERS = 13


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


def _json_new(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    digest = _sha256(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return digest


def _npz_new(path: Path, **arrays: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    np.savez_compressed(path, **arrays)
    digest = _sha256(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return digest


def _authority(absent: bool) -> dict[str, bool]:
    checks = {
        "active_plan": "round: R465" in PLAN.read_text(encoding="utf-8") and "state: active" in PLAN.read_text(encoding="utf-8"),
        "active_line": "line_id: yang-md-decoupling-marl" in LINE.read_text(encoding="utf-8"),
        "r459_verified": (R459 / "checks/verification_report.json").is_file(),
        "r449_present": R449.is_file(),
        "linux_runtime": platform.system() == "Linux",
        "one_native_thread": all(os.environ.get(name) == "1" for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")),
    }
    if absent:
        checks["formal_output_absent"] = not OUT.exists()
    return checks


def _sources() -> dict[str, dict[str, str]]:
    paths = {
        "runner": Path(__file__).resolve(),
        "implementation": ROOT / "src/andes_rl_kundur/evaluation/u5_total_sensitivity.py",
        "plan": PLAN,
        "r459_verification": R459 / "checks/verification_report.json",
        "r459_model": R459 / "model_exports/object_b/sampled_model.npz",
        "r459_continuous": R459 / "model_exports/object_b/continuous_reduced_model.npz",
        "r449_partial": R449,
    }
    return {name: {"path": _relative(path), "sha256": _sha256(path)} for name, path in paths.items()}


def rehearse() -> None:
    if REHEARSAL.exists() or CAPACITY.exists():
        raise FileExistsError("R465 rehearsal/capacity exists")
    authority = _authority(True)
    if not all(authority.values()):
        raise RuntimeError(authority)
    start = time.perf_counter()
    nominal = u5.build_point("nominal", 0.0)
    perturbed = u5.build_point("logD", 0.01)
    complement, gauge = u5.gauge_complement(nominal)
    nominal_reduced, nominal_check = u5.reduce_point(nominal, complement)
    perturbed_reduced, perturbed_check = u5.reduce_point(perturbed, complement)
    h = 0.01
    ac = nominal["arrays"]["A_continuous"]
    bc = nominal["arrays"]["B_continuous"]
    ac_r = (perturbed["arrays"]["A_continuous"] - ac) / h
    bc_r = (perturbed["arrays"]["B_continuous"] - bc) / h
    ad_r, bd_r = u5.zoh_frechet(ac, bc, ac_r, bc_r)
    ad_direct = (perturbed["arrays"]["A_sampled"] - nominal["arrays"]["A_sampled"]) / h
    bd_direct = (perturbed["arrays"]["B_sampled"] - nominal["arrays"]["B_sampled"]) / h
    checks = {
        "authority": authority,
        "nominal_equilibrium": max(nominal["equilibrium_max_abs_f"], nominal["equilibrium_max_abs_g"]),
        "perturbed_equilibrium": max(perturbed["equilibrium_max_abs_f"], perturbed["equilibrium_max_abs_g"]),
        "names_match": nominal["name_hash"] == perturbed["name_hash"],
        "modes_match": nominal["active_mode_hash"] == perturbed["active_mode_hash"],
        "gauge": gauge,
        "nominal_gauge_check": nominal_check,
        "perturbed_gauge_check": perturbed_check,
        "one_sided_zoh_A_relative": u5.discrepancy(ad_r, ad_direct)["relative"],
        "one_sided_zoh_B_relative": u5.discrepancy(bd_r, bd_direct)["relative"],
    }
    passed = bool(
        checks["nominal_equilibrium"] <= 1e-4
        and checks["perturbed_equilibrium"] <= 1e-4
        and checks["names_match"] and checks["modes_match"]
        and gauge["right_residual"] <= 1e-9 and gauge["output_norm"] <= 1e-9
        and nominal_check["gauge_to_reduced_leakage"] <= 1e-9
        and perturbed_check["gauge_to_reduced_leakage"] <= 1e-9
        and checks["one_sided_zoh_A_relative"] <= 0.05
        and checks["one_sided_zoh_B_relative"] <= 0.05
    )
    checks["passed"] = passed
    if not passed:
        raise RuntimeError(checks)
    wall = time.perf_counter() - start
    _json_new(REHEARSAL, {"round": ROUND, "created_utc": _utc(), "checks": checks, "wall_seconds": wall})
    available = None
    try:
        meminfo = Path("/proc/meminfo").read_text(encoding="utf-8")
        available = int(next(line.split()[1] for line in meminfo.splitlines() if line.startswith("MemAvailable:"))) * 1024
    except (OSError, StopIteration, ValueError):
        pass
    _json_new(CAPACITY, {
        "round": ROUND, "created_utc": _utc(), "readiness": "RUN-READY",
        "capacity_anchor": "R460 measured 15 workers plus one orchestrator at 50.96% greater throughput than eight workers",
        "unique_jobs": 13, "selected_workers": WORKERS, "orchestrator_processes": 1,
        "wsl_python_processes": WORKERS + 1, "host_process_budget": 17,
        "native_threads_per_process": 1, "other_reserved_processes": 0,
        "wsl_available_memory_bytes": available, "gpu_selected": False,
        "gpu_reason": "CPU/DAE initialization and small dense linear algebra; no measured GPU path",
        "rehearsal_wall_seconds_for_two_serial_points": wall,
    })
    print(json.dumps(checks, indent=2))


def prepare() -> None:
    if SEAL.exists() or OUT.exists():
        raise FileExistsError("R465 seal/output exists")
    authority = _authority(True)
    if not all(authority.values()):
        raise RuntimeError(authority)
    seal = {
        "round": ROUND, "created_utc": _utc(), "authority": authority,
        "sources": _sources(), "rehearsal_sha256": _sha256(REHEARSAL),
        "capacity_sha256": _sha256(CAPACITY), "formal_output": _relative(OUT),
        "unique_jobs": 13, "workers": WORKERS, "wsl_python_processes": 14,
        "native_threads_per_process": 1, "retry_policy": "none",
        "rho_grid": [0.0, -0.04, 0.04, -0.02, 0.02, -0.01, 0.01],
    }
    print(_json_new(SEAL, seal))


def _verify_seal() -> dict[str, Any]:
    seal = json.loads(SEAL.read_text(encoding="utf-8"))
    for name, row in seal["sources"].items():
        if _sha256(ROOT / row["path"]) != row["sha256"]:
            raise RuntimeError(f"source drift: {name}")
    return seal


def _parallel_points() -> list[dict[str, Any]]:
    context = mp.get_context("spawn")
    specs = u5.point_specs()
    with futures.ProcessPoolExecutor(max_workers=WORKERS, mp_context=context) as pool:
        jobs = [pool.submit(u5.build_point, parameter, rho) for parameter, rho in specs]
        return [job.result() for job in jobs]


def _relative_convergence(table: dict[str, np.ndarray]) -> dict[str, float | bool]:
    return u5.discrepancy(table["R_h2"], table["R_h"])


def _analyse(points: list[dict[str, Any]]) -> dict[str, Any]:
    nominal = next(point for point in points if point["parameter"] == "nominal")
    complement, gauge = u5.gauge_complement(nominal)
    reduced: dict[tuple[str, float], dict[str, np.ndarray]] = {}
    gauge_rows = {}
    for point in points:
        model, check = u5.reduce_point(point, complement)
        reduced[(point["parameter"], point["rho"])] = model
        gauge_rows[point["point_id"]] = check
    nominal_model = reduced[("nominal", 0.0)]
    headroom = nominal["arrays"]["headroom_upper"]
    point_lookup = {(point["parameter"], point["rho"]): point for point in points}
    derivatives: dict[str, dict[str, Any]] = {}
    frequency_payload: dict[str, np.ndarray] = {"frequency_hz": u5.FREQUENCIES_HZ}
    scalar_payload: dict[str, Any] = {}
    checks: dict[str, Any] = {}
    old = json.loads(R449.read_text(encoding="utf-8"))

    # The 26 transfer reconstructions are independent and use one native BLAS
    # thread each. A thread pool keeps their large arrays in shared memory.
    transfer_jobs = {}
    with futures.ThreadPoolExecutor(max_workers=13) as pool:
        for point in points:
            model = nominal_model if point["parameter"] == "nominal" else reduced[(point["parameter"], point["rho"])]
            for kind in ("bandpass", "local_pi"):
                transfer_jobs[(point["parameter"], point["rho"], kind)] = pool.submit(
                    u5.transfer_arrays, model, point["arrays"]["headroom_upper"], kind
                )
        transfers = {key: job.result() for key, job in transfer_jobs.items()}

    nominal_transfers = {
        kind: transfers[("nominal", 0.0, kind)] for kind in ("bandpass", "local_pi")
    }
    for kind, arrays in nominal_transfers.items():
        for key, value in arrays.items():
            frequency_payload[f"{kind}_{key}"] = value

    for parameter in ("logM", "logD"):
        array_tables = {}
        for key in ("A_continuous", "B_continuous", "C_continuous", "D_continuous", "A_post", "B_post", "C_post", "D_post", "headroom_upper"):
            values = {rho: point_lookup[(parameter, rho)]["arrays"][key] for rho in (-0.04, 0.04, -0.02, 0.02, -0.01, 0.01)}
            array_tables[key] = u5.derivative_table(values)
        reduced_derivative = {
            "A": complement.T @ array_tables["A_post"]["derivative"] @ complement,
            "B": complement.T @ array_tables["B_post"]["derivative"],
            "C": array_tables["C_post"]["derivative"] @ complement,
            "D": array_tables["D_post"]["derivative"],
        }
        ad_f, bd_f = u5.zoh_frechet(
            nominal["arrays"]["A_continuous"], nominal["arrays"]["B_continuous"],
            array_tables["A_continuous"]["derivative"], array_tables["B_continuous"]["derivative"],
        )
        zoh_checks = {
            "A": u5.discrepancy(ad_f, array_tables["A_post"]["derivative"]),
            "B": u5.discrepancy(bd_f, array_tables["B_post"]["derivative"]),
        }
        formula = {}
        direct = {}
        energy = {}
        for kind in ("bandpass", "local_pi"):
            formula[kind] = u5.frequency_derivative(
                nominal_model, reduced_derivative, headroom,
                array_tables["headroom_upper"]["derivative"], kind,
            )
            for key, value in formula[kind].items():
                frequency_payload[f"{parameter}_{kind}_{key}_rho"] = value
            g_values = {
                rho: transfers[(parameter, rho, kind)]["G"]
                for rho in (-0.04, 0.04, -0.02, 0.02, -0.01, 0.01)
            }
            g_table = u5.derivative_table(g_values)
            direct[kind] = u5.discrepancy(formula[kind]["G"], g_table["derivative"])
            frequency_payload[f"{parameter}_{kind}_G_direct_rho"] = g_table["derivative"]
            for rho, value in g_values.items():
                frequency_payload[f"{parameter}_{kind}_G_{u5.point_id(parameter, rho)}"] = value
            band_values = {rho: u5.band_energy(g_values[rho]) for rho in g_values}
            band_table = u5.derivative_table(band_values)
            band_formula = u5.band_energy_derivative(nominal_transfers[kind]["G"], formula[kind]["G"])
            window_values = {
                rho: u5.window_energy(reduced[(parameter, rho)], point_lookup[(parameter, rho)]["arrays"]["headroom_upper"], kind)
                for rho in (-0.04, 0.04, -0.02, 0.02, -0.01, 0.01)
            }
            window_table = u5.derivative_table(window_values)
            energy[kind] = {
                "band_nominal": u5.band_energy(nominal_transfers[kind]["G"]),
                "band_formula_derivative": band_formula,
                "band_direct_derivative": float(band_table["derivative"]),
                "band_formula_vs_direct": u5.discrepancy(np.asarray(band_formula), band_table["derivative"]),
                "band_richardson": _relative_convergence(band_table),
                "window_nominal": u5.window_energy(nominal_model, headroom, kind),
                "window_direct_derivative": float(window_table["derivative"]),
                "window_richardson": _relative_convergence(window_table),
                "band_points": {str(rho): value for rho, value in band_values.items()},
                "window_points": {str(rho): value for rho, value in window_values.items()},
            }
        ratio_band = energy["bandpass"]["band_nominal"] / energy["local_pi"]["band_nominal"]
        ratio_band_rho = (
            energy["bandpass"]["band_formula_derivative"] / energy["bandpass"]["band_nominal"]
            - energy["local_pi"]["band_formula_derivative"] / energy["local_pi"]["band_nominal"]
        )
        ratio_window = energy["bandpass"]["window_nominal"] / energy["local_pi"]["window_nominal"]
        ratio_window_rho = (
            energy["bandpass"]["window_direct_derivative"] / energy["bandpass"]["window_nominal"]
            - energy["local_pi"]["window_direct_derivative"] / energy["local_pi"]["window_nominal"]
        )
        old_a_only = old["results"][parameter]["candidate_term"] + old["results"][parameter]["reference_term"]
        non_a = ratio_band_rho - old_a_only
        p1 = "SUPPORTED" if abs(non_a) > 0.01 * max(abs(ratio_band_rho), 1e-12) else "REFUTED"
        convergence = {key: _relative_convergence(value) for key, value in array_tables.items()}
        conditioning = {
            kind: {
                "max_cond_zI_minus_A": float(np.max(nominal_transfers[kind]["cond_zI_minus_A"])),
                "max_cond_I_plus_L": float(np.max(nominal_transfers[kind]["cond_I_plus_L"])),
            } for kind in ("bandpass", "local_pi")
        }
        parameter_checks = {
            "array_richardson": convergence,
            "zoh_frechet": zoh_checks,
            "transfer_formula_vs_direct": direct,
            "energy": energy,
            "conditioning": conditioning,
            "band_ratio": ratio_band,
            "band_log_ratio_derivative": ratio_band_rho,
            "window_ratio": ratio_window,
            "window_log_ratio_derivative": ratio_window_rho,
            "r449_A_only_log_ratio_derivative": old_a_only,
            "non_A_residual": non_a,
            "P1_A_only_sufficiency": p1,
        }
        scalar_payload[parameter] = parameter_checks
        array_pass = all(row["passed"] for row in convergence.values())
        zoh_pass = all(row["relative"] <= 1e-5 or row["max_abs"] <= 1e-9 for row in zoh_checks.values())
        direct_pass = all(row["passed"] for row in direct.values())
        energy_pass = all(
            energy[kind][key]["passed"]
            for kind in ("bandpass", "local_pi")
            for key in ("band_formula_vs_direct", "band_richardson", "window_richardson")
        )
        cond_pass = all(
            np.isfinite(value) and value <= 1e12
            for row in conditioning.values() for value in row.values()
        )
        checks[parameter] = {
            "array_richardson_pass": array_pass, "zoh_frechet_pass": zoh_pass,
            "transfer_direct_pass": direct_pass, "energy_pass": energy_pass,
            "conditioning_pass": cond_pass, "P1": p1,
        }
        derivatives[parameter] = array_tables

    mode_pass = all(point["active_mode_hash"] == nominal["active_mode_hash"] for point in points)
    name_pass = all(point["name_hash"] == nominal["name_hash"] for point in points)
    equilibrium_pass = all(max(point["equilibrium_max_abs_f"], point["equilibrium_max_abs_g"]) <= 1e-4 for point in points)
    gauge_pass = bool(
        gauge["right_residual"] <= 1e-9 and gauge["output_norm"] <= 1e-9
        and all(row["gauge_to_reduced_leakage"] <= 1e-9 and row["maximum_transfer_relative_error"] <= 1e-9 for row in gauge_rows.values())
    )
    numeric_pass = all(
        all(value for key, value in row.items() if key.endswith("_pass"))
        for row in checks.values()
    )
    if not mode_pass:
        verdict = "MODE-SPECIFIC-NOT-TOTAL"
        for row in checks.values():
            row["P1"] = "UNDECIDABLE"
    elif equilibrium_pass and name_pass and gauge_pass and numeric_pass:
        verdict = "TOTAL-SENSITIVITY-VALID"
    else:
        verdict = "TOTAL-DERIVATIVE-INVALID"
        for row in checks.values():
            row["P1"] = "UNDECIDABLE"
    return {
        "verdict": verdict, "points": points, "complement": complement,
        "gauge": gauge, "gauge_rows": gauge_rows, "derivatives": derivatives,
        "frequency_payload": frequency_payload, "scalar_payload": scalar_payload,
        "checks": checks, "mode_pass": mode_pass, "name_pass": name_pass,
        "equilibrium_pass": equilibrium_pass, "gauge_pass": gauge_pass,
    }


def run() -> None:
    if OUT.exists():
        raise FileExistsError(OUT)
    seal = _verify_seal()
    start = time.perf_counter()
    points = _parallel_points()
    analysis = _analyse(points)
    OUT.mkdir(parents=True, exist_ok=False)
    for point in points:
        root = OUT / "parameter_points" / point["point_id"]
        _npz_new(root / "model.npz", **point["arrays"])
        _json_new(root / "metadata.json", {key: value for key, value in point.items() if key not in ("arrays", "source_metrics")} | {"source_metrics": point["source_metrics"]})
    _npz_new(OUT / "derivatives/frequency_arrays.npz", **analysis["frequency_payload"])
    derivative_arrays = {}
    convergence_rows = {}
    for parameter, tables in analysis["derivatives"].items():
        for array_name, table in tables.items():
            for level, value in table.items():
                derivative_arrays[f"{parameter}_{array_name}_{level}"] = value
            convergence_rows[f"{parameter}_{array_name}"] = _relative_convergence(table)
    _npz_new(OUT / "derivatives/model_derivatives.npz", **derivative_arrays)
    _npz_new(OUT / "derivatives/common_gauge_complement.npz", complement=analysis["complement"])
    _json_new(OUT / "checks/gauge_checks.json", {"nominal": analysis["gauge"], "points": analysis["gauge_rows"]})
    _json_new(OUT / "checks/richardson_table.json", convergence_rows)
    _json_new(OUT / "checks/total_sensitivity_checks.json", analysis["scalar_payload"])
    point_registry = [{key: value for key, value in point.items() if key not in ("arrays", "source_metrics", "names")} for point in points]
    _json_new(OUT / "contracts/parameter_points.json", {"grid": [0.0, -0.04, 0.04, -0.02, 0.02, -0.01, 0.01], "parameters": ["logM", "logD"], "points": point_registry})
    verification = {
        "round": ROUND, "created_utc": _utc(), "verdict": analysis["verdict"],
        "formal_seal_sha256": _sha256(SEAL), "unique_parameter_points": len(points),
        "mode_pass": analysis["mode_pass"], "name_pass": analysis["name_pass"],
        "equilibrium_pass": analysis["equilibrium_pass"], "gauge_pass": analysis["gauge_pass"],
        "parameter_checks": analysis["checks"],
        "all_checks_pass": analysis["verdict"] == "TOTAL-SENSITIVITY-VALID",
    }
    _json_new(OUT / "checks/verification_report.json", verification)
    _json_new(OUT / "provenance/runtime.json", {
        "wall_seconds": time.perf_counter() - start, "python": sys.version,
        "platform": platform.platform(), "numpy": np.__version__, "scipy": scipy.__version__,
        "workers": WORKERS, "native_threads_per_process": 1,
        "formal_seal_sha256": _sha256(SEAL), "seal": seal,
    })
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    (OUT / "SHA256SUMS").write_text("".join(f"{_sha256(path)}  {path.relative_to(OUT).as_posix()}\n" for path in files), encoding="utf-8", newline="\n")
    print(json.dumps(verification, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("command", choices=("rehearse", "prepare", "run")); args = parser.parse_args()
    {"rehearse": rehearse, "prepare": prepare, "run": run}[args.command]()


if __name__ == "__main__":
    main()
