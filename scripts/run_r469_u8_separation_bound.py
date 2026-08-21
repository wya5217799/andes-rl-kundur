"""R469 U8 I/O separation bounds and heterogeneity scaling (WSL only)."""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import csv
import hashlib
import json
import multiprocessing as mp
import os
import platform
import subprocess
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
import scipy.linalg as la  # noqa: E402

from andes_rl_kundur.evaluation import u8_separation_bound as u8  # noqa: E402
from andes_rl_kundur.evaluation.u1_u8_shared_export import runtime_manifest  # noqa: E402

ROUND = "R469"
PLAN = ROOT / "memory/rounds/R469/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
CAPACITY = ROOT / "memory/rounds/R469/capacity_evidence.json"
REHEARSAL = ROOT / "memory/rounds/R469/rehearsal.json"
SEAL = ROOT / "memory/rounds/R469/formal_seal.json"
OUT = ROOT / "results/research_loop/r469_u8_separation_bound"
R405 = ROOT / "results/research_loop/r405_homogenization_gate/linearization_matrices.json"
R459 = ROOT / "results/research_loop/r459_u1_u8_shared_export"
R468 = ROOT / "results/research_loop/r468_u7_local_taylor/checks/verification_report.json"
REQUEST = (
    ROOT
    / "paper/yang_md_decoupling_marl/working/gpt_pro_additional_data_request_20260821/05_acceptance_tests_and_stop_rules.md"
)
SOLUTION = (
    ROOT
    / "paper/yang_md_decoupling_marl/working/gpt_pro_unresolved_math_solution_20260821/01_complete_solution.md"
)
CHECKER = ROOT / "probes/r469_u8_independent_check.py"
WORKERS = 15


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


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, complex):
        return {"real": float(value.real), "imag": float(value.imag)}
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _json_new(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    path.write_text(
        json.dumps(_jsonable(payload), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    digest = _sha256(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return digest


def _npz_new(path: Path, **arrays: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    np.savez_compressed(path, **{name: np.asarray(value) for name, value in arrays.items()})
    digest = _sha256(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return digest


def _profiles() -> dict[str, dict[str, np.ndarray]]:
    payload = json.loads(R405.read_text(encoding="utf-8"))
    return {
        name: {
            "M": np.asarray(row["baseline_m0"], dtype=float),
            "D": np.asarray(row["baseline_d0"], dtype=float),
        }
        for name, row in payload["profiles"].items()
    }


def _specs() -> list[tuple[str, np.ndarray, np.ndarray, float]]:
    return [
        (profile_id, values["M"], values["D"], alpha)
        for profile_id, values in _profiles().items()
        for alpha in u8.ALPHAS
    ]


def _authority(absent: bool) -> dict[str, bool]:
    checks = {
        "active_plan": "round: R469" in PLAN.read_text(encoding="utf-8")
        and "state: active" in PLAN.read_text(encoding="utf-8"),
        "active_line": "line_id: yang-md-decoupling-marl" in LINE.read_text(encoding="utf-8"),
        "r405_present": R405.is_file(),
        "r459_verified": (R459 / "checks/verification_report.json").is_file(),
        "r468_present": R468.is_file(),
        "request_present": REQUEST.is_file(),
        "solution_present": SOLUTION.is_file(),
        "checker_present": CHECKER.is_file(),
        "linux_runtime": platform.system() == "Linux",
        "one_native_thread": all(
            os.environ.get(name) == "1"
            for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
        ),
    }
    if absent:
        checks["formal_output_absent"] = not OUT.exists()
    return checks


def _sources() -> dict[str, dict[str, str]]:
    paths = {
        "runner": Path(__file__).resolve(),
        "implementation": ROOT / "src/andes_rl_kundur/evaluation/u8_separation_bound.py",
        "checker": CHECKER,
        "plan": PLAN,
        "r405_profiles": R405,
        "r459_verification": R459 / "checks/verification_report.json",
        "r468_verification": R468,
        "request": REQUEST,
        "solution": SOLUTION,
    }
    return {
        name: {"path": _relative(path), "sha256": _sha256(path)} for name, path in paths.items()
    }


def _point_pair() -> tuple[dict[str, Any], dict[str, Any]]:
    profile_id, values = next(iter(_profiles().items()))
    return (
        u8.build_point(profile_id, values["M"], values["D"], 0.0),
        u8.build_point(profile_id, values["M"], values["D"], 1.0),
    )


def rehearse() -> None:
    if REHEARSAL.exists() or CAPACITY.exists():
        raise FileExistsError("R469 rehearsal/capacity exists")
    authority = _authority(True)
    if not all(authority.values()):
        raise RuntimeError(authority)
    start = time.perf_counter()
    nominal, corner = _point_pair()
    complement, gauge = u8.gauge_complement(nominal)
    model = u8.quotient(nominal, complement)
    lift = u8.toeplitz_lift(model)
    direct = u8.direct_impulse_lift(model)
    projectors = u8.projectors()
    checks = {
        "authority": authority,
        "projectors": u8.projector_checks(projectors),
        "gauge": gauge,
        "nominal_residual": max(nominal["equilibrium_max_abs_f"], nominal["equilibrium_max_abs_g"]),
        "corner_residual": max(corner["equilibrium_max_abs_f"], corner["equilibrium_max_abs_g"]),
        "names_match": nominal["name_hash"] == corner["name_hash"],
        "modes_match": nominal["active_mode_hash"] == corner["active_mode_hash"],
        "quotient_dimensions": {key: list(value.shape) for key, value in model.items()},
        "lift_shape": list(lift.shape),
        "lift_direct_max_abs_error": float(np.max(np.abs(lift - direct))),
        "finite": bool(
            np.all(np.isfinite(lift))
            and all(np.all(np.isfinite(value)) for value in model.values())
        ),
    }
    checks["passed"] = bool(
        checks["projectors"]["passed"]
        and checks["nominal_residual"] <= 1.0e-8
        and checks["corner_residual"] <= 1.0e-8
        and checks["names_match"]
        and checks["modes_match"]
        and checks["finite"]
        and checks["lift_shape"] == [90, 30]
        and checks["lift_direct_max_abs_error"] <= 1.0e-10
        and gauge["right_residual"] <= 1.0e-9
        and gauge["output_norm"] <= 1.0e-9
    )
    if not checks["passed"]:
        raise RuntimeError(checks)
    checks["wall_seconds"] = time.perf_counter() - start
    _json_new(REHEARSAL, checks)
    available = None
    try:
        meminfo = Path("/proc/meminfo").read_text(encoding="utf-8")
        available = (
            int(
                next(
                    row.split()[1]
                    for row in meminfo.splitlines()
                    if row.startswith("MemAvailable:")
                )
            )
            * 1024
        )
    except (OSError, StopIteration, ValueError):
        pass
    _json_new(
        CAPACITY,
        {
            "round": ROUND,
            "created_utc": _utc(),
            "readiness": "RUN-READY",
            "capacity_anchor": "R460 measured 15 workers plus one orchestrator at 50.96% greater throughput than eight workers",
            "unique_jobs": len(_specs()),
            "selected_workers": WORKERS,
            "orchestrator_processes": 1,
            "wsl_python_processes": WORKERS + 1,
            "host_process_budget": 17,
            "native_threads_per_process": 1,
            "other_reserved_processes": 0,
            "wsl_available_memory_bytes": available,
            "gpu_selected": False,
            "gpu_reason": "No CUDA ANDES path and small dense response matrices",
            "rehearsal_wall_seconds_for_two_serial_points": checks["wall_seconds"],
        },
    )
    print(json.dumps(checks, indent=2))


def prepare() -> None:
    if SEAL.exists() or OUT.exists():
        raise FileExistsError("R469 seal/output exists")
    authority = _authority(True)
    if not all(authority.values()):
        raise RuntimeError(authority)
    seal = {
        "round": ROUND,
        "created_utc": _utc(),
        "authority": authority,
        "sources": _sources(),
        "rehearsal_sha256": _sha256(REHEARSAL),
        "capacity_sha256": _sha256(CAPACITY),
        "formal_output": _relative(OUT),
        "unique_jobs": len(_specs()),
        "workers": WORKERS,
        "wsl_python_processes": WORKERS + 1,
        "native_threads_per_process": 1,
        "retry_policy": "none",
        "alphas": list(u8.ALPHAS),
        "frequency_points": len(u8.FREQUENCIES_HZ),
        "horizon": u8.HORIZON,
        "full_state_projector": "prohibited-unverified",
    }
    print(_json_new(SEAL, seal))


def _verify_seal() -> dict[str, Any]:
    seal = json.loads(SEAL.read_text(encoding="utf-8"))
    if not all(_authority(False).values()):
        raise RuntimeError(_authority(False))
    for name, row in seal["sources"].items():
        if _sha256(ROOT / row["path"]) != row["sha256"]:
            raise RuntimeError(f"source drift: {name}")
    return seal


def _parallel_points() -> list[dict[str, Any]]:
    context = mp.get_context("spawn")
    with futures.ProcessPoolExecutor(max_workers=WORKERS, mp_context=context) as pool:
        jobs = [pool.submit(u8.build_point, *spec) for spec in _specs()]
        return [job.result() for job in jobs]


def _analyse_one(point: dict[str, Any]) -> dict[str, Any]:
    complement, gauge = u8.gauge_complement(point)
    model = u8.quotient(point, complement)
    lift = u8.toeplitz_lift(model)
    direct_error = float(np.max(np.abs(lift - u8.direct_impulse_lift(model))))
    frequency = u8.frequency_table(model)
    stiffness = u8.stiffness_table(model)
    return {
        "point": point,
        "complement": complement,
        "model": model,
        "gauge": gauge,
        "lift": lift,
        "direct_error": direct_error,
        "frequency": frequency,
        "stiffness": stiffness,
    }


def _scaling(
    rows: list[dict[str, Any]], profiles: dict[str, dict[str, np.ndarray]]
) -> list[dict[str, Any]]:
    result = []
    lookup = {(row["point"]["profile_id"], row["point"]["alpha"]): row for row in rows}
    for profile_id, values in profiles.items():
        baseline = lookup[(profile_id, 0.0)]
        entries = []
        for alpha in u8.ALPHAS:
            row = lookup[(profile_id, alpha)]
            delta = row["lift"] - baseline["lift"]
            entries.append(
                {
                    "alpha": alpha,
                    "lift_cross_norm": float(la.svdvals(row["lift"])[0]),
                    "lift_cross_energy_gain": float(la.svdvals(row["lift"])[0] ** 2),
                    "delta_lift_spectral_norm": float(la.svdvals(delta)[0]),
                    "delta_lift_norm_over_alpha": None
                    if alpha == 0
                    else float(la.svdvals(delta)[0] / alpha),
                    "maximum_frequency_cross_norm": float(np.max(row["frequency"]["cross_norm"])),
                }
            )
        m, d = values["M"], values["D"]
        result.append(
            {
                "profile_id": profile_id,
                "M_values": m.tolist(),
                "D_values": d.tolist(),
                "mean_M": float(np.mean(m)),
                "mean_D": float(np.mean(d)),
                "delta_M": float(np.std(m)),
                "delta_D": float(np.std(d)),
                "CV_M": float(np.std(m) / np.mean(m)),
                "CV_D": float(np.std(d) / np.mean(d)),
                "network_asymmetry_intercept_lift_norm": entries[0]["lift_cross_norm"],
                "alpha_rows": entries,
                "positive_alpha_normalized_spread": float(
                    np.ptp([entry["delta_lift_norm_over_alpha"] for entry in entries[1:]])
                    / max(
                        np.mean([entry["delta_lift_norm_over_alpha"] for entry in entries[1:]]),
                        1.0e-15,
                    )
                ),
            }
        )
    return result


def _write_bound_csv(path: Path, rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    fields = [
        "profile_id",
        "alpha",
        "frequency_hz",
        "epsilon_A",
        "epsilon_B",
        "epsilon_C",
        "epsilon_D",
        "resolvent_condition",
        "actual_cross_norm",
        "upper_bound",
        "lower_bound",
        "bound_slack",
        "sigma_min_Zdd",
        "abs_Sc",
        "mode_hash",
        "gauge_valid",
        "effective_stiffness_valid",
    ]
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            point, frequency, stiffness = row["point"], row["frequency"], row["stiffness"]
            for index, frequency_hz in enumerate(stiffness["frequency_hz"]):
                actual, upper = (
                    stiffness["actual_cross_norm"][index],
                    stiffness["upper_bound"][index],
                )
                writer.writerow(
                    {
                        "profile_id": point["profile_id"],
                        "alpha": point["alpha"],
                        "frequency_hz": frequency_hz,
                        "epsilon_A": "unavailable-no-Px",
                        "epsilon_B": "unavailable-no-Px",
                        "epsilon_C": "unavailable-no-Px",
                        "epsilon_D": frequency["epsilon_D"][index + 1],
                        "resolvent_condition": frequency["resolvent_condition"][index + 1],
                        "actual_cross_norm": actual,
                        "upper_bound": upper,
                        "lower_bound": stiffness["lower_bound"][index],
                        "bound_slack": upper - actual if stiffness["valid"][index] else "",
                        "sigma_min_Zdd": stiffness["sigma_min_Zdd"][index],
                        "abs_Sc": stiffness["abs_Sc"][index],
                        "mode_hash": point["active_mode_hash"],
                        "gauge_valid": row["gauge"]["right_residual"] <= 1.0e-9,
                        "effective_stiffness_valid": stiffness["valid"][index],
                    }
                )
    digest = _sha256(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return digest


def run() -> None:
    _verify_seal()
    if OUT.exists():
        raise FileExistsError(OUT)
    OUT.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    points = _parallel_points()
    with futures.ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(_analyse_one, points))
    profiles = _profiles()
    projector_values = u8.projectors()
    projector_report = u8.projector_checks(projector_values)

    _json_new(
        OUT / "contracts/schema.json",
        {
            "round": ROUND,
            "profile_ids": list(profiles),
            "alphas": list(u8.ALPHAS),
            "frequency_grid_hz": [0.0, 2.5, len(u8.FREQUENCIES_HZ)],
            "sample_period_seconds": u8.DT,
            "horizon_steps": u8.HORIZON,
            "input_basis": "common qc=ones(4)/2",
            "output_basis": "registered orthonormal three-row differential basis",
            "full_state_projector": None,
            "full_state_projector_reason": "101 quotient states include asymmetric network coordinates with no verified device-permutation representation",
            "epsilon_A": "unavailable",
            "epsilon_B": "unavailable",
            "epsilon_C": "unavailable",
            "epsilon_D": "direct I/O feedthrough cross norm only",
        },
    )
    _npz_new(OUT / "contracts/projectors.npz", **projector_values, q_c=u8.Q_C, T_d=u8.T_D)
    _json_new(OUT / "contracts/projector_checks.json", projector_report)
    _json_new(
        OUT / "contracts/full_state_projector_unavailable.json",
        {
            "P_x": None,
            "Q_x": None,
            "commutator_A_Px": None,
            "status": "NOT-COMPUTED-BY-DESIGN",
            "reason": "no physical full-state symmetry action verified",
            "prohibited_operation": "padding four frequency projectors into the 101-state quotient",
        },
    )

    point_index = []
    for row in rows:
        point, model = row["point"], row["model"]
        raw_arrays = {**point["arrays"]}
        for key, value in model.items():
            raw_arrays[f"{key}_quotient" if key != "D_post" else "D_post"] = value
        raw_path = OUT / f"parameter_points/{point['point_id']}.npz"
        lift_path = OUT / f"lifts/{point['point_id']}.npz"
        freq_path = OUT / f"frequency/{point['point_id']}.npz"
        stiff_path = OUT / f"effective_stiffness/{point['point_id']}.npz"
        _npz_new(raw_path, **raw_arrays, gauge_complement=row["complement"])
        _npz_new(lift_path, H=row["lift"], singular_values=la.svdvals(row["lift"]))
        _npz_new(freq_path, **row["frequency"])
        _npz_new(stiff_path, **row["stiffness"])
        point_index.append(
            {
                "profile_id": point["profile_id"],
                "alpha": point["alpha"],
                "point_id": point["point_id"],
                "M_values": point["M_values"].tolist(),
                "D_values": point["D_values"].tolist(),
                "name_hash": point["name_hash"],
                "active_mode_hash": point["active_mode_hash"],
                "equilibrium_max_abs_f": point["equilibrium_max_abs_f"],
                "equilibrium_max_abs_g": point["equilibrium_max_abs_g"],
                "algebraic_reciprocal_condition": point["algebraic_reciprocal_condition"],
                "gauge": row["gauge"],
                "direct_impulse_max_abs_error": row["direct_error"],
                "npz": raw_path.relative_to(OUT).as_posix(),
                "lift_npz": lift_path.relative_to(OUT).as_posix(),
                "frequency_npz": freq_path.relative_to(OUT).as_posix(),
                "stiffness_npz": stiff_path.relative_to(OUT).as_posix(),
            }
        )
    _json_new(OUT / "parameter_points/index.json", point_index)
    scaling = _scaling(rows, profiles)
    _json_new(OUT / "scaling/heterogeneity_scaling.json", scaling)
    _write_bound_csv(OUT / "bounds/bound_table.csv", rows)

    max_lift_error = max(row["direct_error"] for row in rows)
    max_residual = max(
        max(row["point"]["equilibrium_max_abs_f"], row["point"]["equilibrium_max_abs_g"])
        for row in rows
    )
    mode_pass = len({row["point"]["active_mode_hash"] for row in rows}) == 1
    name_pass = len({row["point"]["name_hash"] for row in rows}) == 1
    valid_stiffness = np.concatenate([row["stiffness"]["valid"] for row in rows])
    actual = np.concatenate(
        [row["stiffness"]["actual_cross_norm"][row["stiffness"]["valid"]] for row in rows]
    )
    upper = np.concatenate(
        [row["stiffness"]["upper_bound"][row["stiffness"]["valid"]] for row in rows]
    )
    lower = np.concatenate(
        [row["stiffness"]["lower_bound"][row["stiffness"]["valid"]] for row in rows]
    )
    upper_violation = float(np.max(actual - upper)) if len(actual) else float("inf")
    lower_violation = float(np.max(lower - actual)) if len(actual) else float("inf")
    reconstruction = max(
        float(np.max(row["stiffness"]["reconstruction_error"][row["stiffness"]["valid"]]))
        for row in rows
    )
    checks = {
        "projectors_pass": projector_report["passed"],
        "full_state_projector_exported": False,
        "full_state_projector_status": "NOT-COMPUTED-BY-DESIGN",
        "mode_hash_all_equal": mode_pass,
        "name_hash_all_equal": name_pass,
        "maximum_equilibrium_residual": max_residual,
        "maximum_direct_impulse_lift_error": max_lift_error,
        "effective_stiffness_valid_points": int(np.sum(valid_stiffness)),
        "effective_stiffness_total_points": int(len(valid_stiffness)),
        "maximum_upper_bound_violation": upper_violation,
        "maximum_lower_bound_violation": lower_violation,
        "maximum_block_reconstruction_error": reconstruction,
        "maximum_resolvent_condition": max(
            float(np.max(row["frequency"]["resolvent_condition"])) for row in rows
        ),
    }
    checks["all_checks_pass"] = bool(
        checks["projectors_pass"]
        and mode_pass
        and name_pass
        and max_residual <= 1.0e-8
        and max_lift_error <= 1.0e-10
        and np.all(valid_stiffness)
        and upper_violation <= 1.0e-8
        and lower_violation <= 1.0e-8
        and reconstruction <= 1.0e-8
    )
    checks["verdict"] = "IO-BOUND-COMPLETE" if checks["all_checks_pass"] else "BOUND-INCOMPLETE"
    _json_new(
        OUT / "checks/verification_report.json",
        {"round": ROUND, "created_utc": _utc(), "formal_seal_sha256": _sha256(SEAL), **checks},
    )
    _json_new(OUT / "provenance/runtime.json", runtime_manifest(ROOT))

    subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            str(OUT),
            "--write",
            str(OUT / "checks/independent_check.json"),
        ],
        cwd=ROOT,
        check=True,
    )
    _json_new(
        OUT / "claim_evidence_map.json",
        {
            "claim_id": "U8-io-separation-bound",
            "scope": "eight R405 profiles, four heterogeneity scales, fixed topology, local models",
            "status": "supported-qualified" if checks["all_checks_pass"] else "incomplete",
            "raw_inputs": [
                {"path": _relative(R405), "sha256": _sha256(R405)},
                {
                    "path": _relative(R459 / "checks/verification_report.json"),
                    "sha256": _sha256(R459 / "checks/verification_report.json"),
                },
            ],
            "derived_fields": [
                {
                    "path": "bounds/bound_table.csv",
                    "field": "all 32768 nonzero-frequency point rows",
                },
                {"path": "scaling/heterogeneity_scaling.json", "json_pointer": ""},
                {"path": "checks/verification_report.json", "json_pointer": ""},
            ],
            "independent_checks": [{"path": "checks/independent_check.json", "status": "pass"}],
            "authorized_wording": "The finite-window and pointwise I/O cross maps obey the declared effective-stiffness bounds on the registered local models; heterogeneity alone does not determine cross response.",
            "prohibited_wording": [
                "full-state commutator bound",
                "universal heterogeneity trade-off",
                "robust separation certificate",
            ],
        },
    )

    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    (OUT / "SHA256SUMS").write_text(
        "\n".join(f"{_sha256(path)}  {path.relative_to(OUT).as_posix()}" for path in files) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {**checks, "wall_seconds": time.perf_counter() - start, "files": len(files) + 1},
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("rehearse", "prepare", "run"))
    args = parser.parse_args()
    {"rehearse": rehearse, "prepare": prepare, "run": run}[args.mode]()


if __name__ == "__main__":
    main()
