"""R468 U7 complete physical-parameter tensors and 30-step lifted maps."""

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
import scipy.linalg as la  # noqa: E402

from andes_rl_kundur.evaluation import u5_total_sensitivity as u5  # noqa: E402
from andes_rl_kundur.evaluation import u7_local_taylor as u7  # noqa: E402
from andes_rl_kundur.evaluation.u1_u8_shared_export import runtime_manifest  # noqa: E402

ROUND = "R468"
PLAN = ROOT / "memory/rounds/R468/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
CAPACITY = ROOT / "memory/rounds/R468/capacity_evidence.json"
REHEARSAL = ROOT / "memory/rounds/R468/rehearsal.json"
SEAL = ROOT / "memory/rounds/R468/formal_seal.json"
OUT = ROOT / "results/research_loop/r468_u7_local_taylor"
R444 = ROOT / "results/research_loop/r444_signed_probe_order/formal_analysis.json"
R446 = ROOT / "results/research_loop/r446_md_authority_fd/formal_analysis.json"
R459 = ROOT / "results/research_loop/r459_u1_u8_shared_export"
REQUEST = (
    ROOT
    / "paper/yang_md_decoupling_marl/working/gpt_pro_additional_data_request_20260821/05_acceptance_tests_and_stop_rules.md"
)
SOLUTION = (
    ROOT
    / "paper/yang_md_decoupling_marl/working/gpt_pro_unresolved_math_solution_20260821/SOURCE_VERIFICATION.md"
)
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


def _json_new(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
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


def _authority(absent: bool) -> dict[str, bool]:
    checks = {
        "active_plan": "round: R468" in PLAN.read_text(encoding="utf-8")
        and "state: active" in PLAN.read_text(encoding="utf-8"),
        "active_line": "line_id: yang-md-decoupling-marl" in LINE.read_text(encoding="utf-8"),
        "r444_present": R444.is_file(),
        "r446_present": R446.is_file(),
        "r459_verified": (R459 / "checks/verification_report.json").is_file(),
        "request_present": REQUEST.is_file(),
        "qualification_present": SOLUTION.is_file(),
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
        "implementation": ROOT / "src/andes_rl_kundur/evaluation/u7_local_taylor.py",
        "plan": PLAN,
        "r444_amplitudes": R444,
        "r446_authority": R446,
        "r459_verification": R459 / "checks/verification_report.json",
        "request": REQUEST,
        "qualification": SOLUTION,
    }
    return {
        name: {"path": _relative(path), "sha256": _sha256(path)} for name, path in paths.items()
    }


def rehearse() -> None:
    if REHEARSAL.exists() or CAPACITY.exists():
        raise FileExistsError("R468 rehearsal/capacity exists")
    authority = _authority(True)
    if not all(authority.values()):
        raise RuntimeError(authority)
    start = time.perf_counter()
    nominal = u7.build_point(-1, 0.0)
    corner = u7.build_point(0, 1.0)
    complement, gauge = u7.gauge_complement(nominal)
    q_nominal = u7.quotient_arrays(nominal, complement)
    q_corner = u7.quotient_arrays(corner, complement)
    payload = {
        "round": ROUND,
        "authority": authority,
        "nominal_dimensions": {name: list(value.shape) for name, value in q_nominal.items()},
        "corner_dimensions": {name: list(value.shape) for name, value in q_corner.items()},
        "gauge": gauge,
        "nominal_residual": max(nominal["equilibrium_max_abs_f"], nominal["equilibrium_max_abs_g"]),
        "corner_residual": max(corner["equilibrium_max_abs_f"], corner["equilibrium_max_abs_g"]),
        "names_match": nominal["name_hash"] == corner["name_hash"],
        "modes_match": nominal["active_mode_hash"] == corner["active_mode_hash"],
        "finite": all(
            np.all(np.isfinite(value)) for value in [*q_nominal.values(), *q_corner.values()]
        ),
    }
    payload["passed"] = bool(
        payload["nominal_residual"] <= 1.0e-8
        and payload["corner_residual"] <= 1.0e-8
        and payload["names_match"]
        and payload["modes_match"]
        and payload["finite"]
        and gauge["right_residual"] <= 1.0e-9
        and gauge["output_norm"] <= 1.0e-9
        and q_nominal["A_post"].shape == (101, 101)
        and q_nominal["B_post"].shape == (101, 7)
    )
    if not payload["passed"]:
        raise RuntimeError(payload)
    payload["wall_seconds"] = time.perf_counter() - start
    _json_new(REHEARSAL, payload)
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
            "unique_jobs": len(u7.point_specs()),
            "selected_workers": WORKERS,
            "orchestrator_processes": 1,
            "wsl_python_processes": WORKERS + 1,
            "host_process_budget": 17,
            "native_threads_per_process": 1,
            "other_reserved_processes": 0,
            "wsl_available_memory_bytes": available,
            "gpu_selected": False,
            "gpu_reason": "No CUDA path for ANDES DAE initialization; matrices are small enough for CPU dense algebra",
            "rehearsal_wall_seconds_for_two_serial_points": payload["wall_seconds"],
        },
    )
    print(json.dumps(payload, indent=2))


def prepare() -> None:
    if SEAL.exists() or OUT.exists():
        raise FileExistsError("R468 seal/output exists")
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
        "unique_jobs": len(u7.point_specs()),
        "workers": WORKERS,
        "wsl_python_processes": WORKERS + 1,
        "native_threads_per_process": 1,
        "retry_policy": "none",
        "parameter_names": list(u7.PARAMETER_NAMES),
        "base_steps": u7.BASE_STEPS.tolist(),
        "levels": list(u7.LEVELS),
        "horizon": u7.HORIZON,
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
        jobs = [
            pool.submit(u7.build_point, parameter, delta) for parameter, delta in u7.point_specs()
        ]
        return [job.result() for job in jobs]


def _swing_formula_checks(
    nominal: dict[str, Any], full_levels: dict[str, np.ndarray]
) -> list[dict[str, Any]]:
    selected = full_levels["A_continuous"][:, 2]
    dynamic = nominal["arrays"]["dynamic_state_indices"].tolist()
    omega_addresses = nominal["arrays"]["omega_state_addresses"].tolist()
    rows = []
    a = nominal["arrays"]["A_continuous"]
    for parameter in range(8):
        device = parameter if parameter < 4 else parameter - 4
        row_index = dynamic.index(int(omega_addresses[device]))
        expected = np.zeros_like(a)
        if parameter < 4:
            expected[row_index] = -a[row_index] / float(nominal["M_values"][device])
        else:
            expected[row_index, row_index] = -1.0 / float(nominal["M_values"][device])
        difference = selected[parameter] - expected
        rows.append(
            {
                "parameter": u7.PARAMETER_NAMES[parameter],
                "omega_row": row_index,
                "expected_norm2": float(np.linalg.norm(expected)),
                "measured_norm2": float(np.linalg.norm(selected[parameter])),
                "max_abs_error": float(np.max(np.abs(difference))),
                "relative_error": float(
                    np.linalg.norm(difference) / max(np.linalg.norm(expected), 1.0e-15)
                ),
            }
        )
    return rows


def _policy_checks() -> dict[str, Any]:
    from andes_rl_kundur.control.per_vsg_md import (
        LocalNeighbourMDContract,
        LocalNeighbourMDExecution,
    )

    controller = LocalNeighbourMDExecution(
        LocalNeighbourMDContract(inertia_gain=2.0, damping_gain=2.0)
    )
    zero = {actor: np.zeros(7, dtype=float) for actor in range(4)}
    zero_action = controller.act(zero)
    h = 1.0e-6
    plus = zero[0].copy()
    plus[1] = h
    minus = zero[0].copy()
    minus[1] = -h
    controller.reset()
    action_plus = controller.act({**zero, 0: plus})
    controller.reset()
    action_minus = controller.act({**zero, 0: minus})
    right = action_plus / h
    left = -action_minus / h
    return {
        "zero_action": zero_action.tolist(),
        "zero_bias_max_abs": float(np.max(np.abs(zero_action))),
        "direction": "agent_1 own frequency",
        "h": h,
        "right_derivative": right.tolist(),
        "left_derivative": left.tolist(),
        "one_sided_derivative_max_abs_difference": float(np.max(np.abs(right - left))),
        "normalized_decoder_positive_slope": 600.0,
        "normalized_decoder_negative_slope": 200.0,
        "smooth_normalized_policy_taylor_applicable": False,
        "reason": "absolute-value policy branches and unequal normalized decoder one-sided slopes at zero",
    }


def _r444_scaling(additive_lift: np.ndarray) -> dict[str, Any]:
    source = json.loads(R444.read_text(encoding="utf-8"))
    blocks = []
    for block in source["blocks"]:
        eps = np.asarray(block["magnitudes"], dtype=float)
        norm = np.asarray(block["delta_odd_norms"], dtype=float)
        linear = norm / eps
        quadratic = norm / eps**2
        stability = abs(quadratic[-1] - quadratic[-2]) / max(abs(quadratic[-1]), 1.0e-15)
        blocks.append(
            {
                "profile_id": block["profile_id"],
                "pair_kind": block["pair_kind"],
                "epsilon": eps.tolist(),
                "delta_y_md_norm": norm.tolist(),
                "delta_y_md_norm_over_epsilon": linear.tolist(),
                "delta_y_md_norm_over_epsilon_squared": quadratic.tolist(),
                "last_two_quadratic_relative_difference": float(stability),
                "linear_normalized_trends_down": bool(linear[-1] < linear[-2]),
                "last_two_quadratic_stable_20pct": bool(stability <= 0.2),
                "classification": block["classification"],
                "mode_consistency": block["mode_consistency"],
            }
        )
    _, singular_values, vh = la.svd(additive_lift, full_matrices=False)
    command = vh[0]
    eps = np.asarray(source["blocks"][0]["magnitudes"], dtype=float)
    additive_norms = np.asarray(
        [np.linalg.norm(additive_lift @ (value * command)) for value in eps]
    )
    return {
        "r444_source_sha256": _sha256(R444),
        "r444_trajectory_count": 288,
        "r444_window_steps": 30,
        "blocks": blocks,
        "md_all_blocks_quadratic": all(row["classification"] == "QUADRATIC" for row in blocks),
        "md_all_last_two_quadratic_stable_20pct": all(
            row["last_two_quadratic_stable_20pct"] for row in blocks
        ),
        "md_all_linear_normalized_trend_down": all(
            row["linear_normalized_trends_down"] for row in blocks
        ),
        "additive_probe": {
            "basis": "unit principal right-singular vector of 30-step differential command lift",
            "epsilon": eps.tolist(),
            "delta_y_additive_norm": additive_norms.tolist(),
            "delta_y_additive_norm_over_epsilon": (additive_norms / eps).tolist(),
            "sigma_max": float(singular_values[0]),
            "nonzero": bool(singular_values[0] > 1.0e-9),
            "relative_spread": float(
                np.ptp(additive_norms / eps) / max(np.mean(additive_norms / eps), 1.0e-15)
            ),
        },
    }


def _run_analysis(points: list[dict[str, Any]]) -> dict[str, Any]:
    nominal = next(point for point in points if point["parameter"] < 0)
    complement, gauge = u7.gauge_complement(nominal)
    quotient = {
        (point["parameter"], point["delta"]): u7.quotient_arrays(point, complement)
        for point in points
    }
    full = {(point["parameter"], point["delta"]): point["arrays"] for point in points}
    keys = (
        "A_continuous",
        "B_continuous",
        "C_continuous",
        "D_continuous",
        "A_post",
        "B_post",
        "C_post",
        "D_post",
    )
    quotient_levels = {key: u7.derivative_levels(quotient, key) for key in keys}
    full_levels = {key: u7.derivative_levels(full, key) for key in keys}
    convergence = {key: u7.convergence(value) for key, value in quotient_levels.items()}
    selected = {key: value[:, 2] for key, value in quotient_levels.items()}
    nominal_q = quotient[(-1, 0.0)]

    zoh_checks = []
    for parameter in range(8):
        ad, bd = u5.zoh_frechet(
            nominal_q["A_continuous"],
            nominal_q["B_continuous"],
            selected["A_continuous"][parameter],
            selected["B_continuous"][parameter],
        )
        zoh_checks.append(
            {
                "parameter": u7.PARAMETER_NAMES[parameter],
                "A": u5.discrepancy(ad, selected["A_post"][parameter]),
                "B": u5.discrepancy(bd, selected["B_post"][parameter]),
            }
        )

    additive = u7.additive_lift(
        nominal_q["A_post"], nominal_q["B_post"], nominal_q["C_post"], nominal_q["D_post"]
    )
    singular_values = la.svdvals(additive)
    bilinear = u7.bilinear_lift(
        nominal_q["A_post"],
        nominal_q["C_post"],
        selected["A_post"],
        selected["B_post"],
        selected["C_post"],
        selected["D_post"],
    )
    scaling = _r444_scaling(additive)
    policy = _policy_checks()
    mode_pass = all(point["active_mode_hash"] == nominal["active_mode_hash"] for point in points)
    name_pass = all(point["name_hash"] == nominal["name_hash"] for point in points)
    max_residual = max(
        max(point["equilibrium_max_abs_f"], point["equilibrium_max_abs_g"]) for point in points
    )
    tensor_pass = all(row["passed"] for rows in convergence.values() for row in rows)
    zoh_pass = all(
        (row[key]["relative"] <= 1.0e-5 or row[key]["max_abs"] <= 1.0e-9)
        for row in zoh_checks
        for key in ("A", "B")
    )
    additive_pass = (
        scaling["additive_probe"]["nonzero"]
        and scaling["additive_probe"]["relative_spread"] <= 0.01
    )
    physical_pass = bool(
        mode_pass
        and name_pass
        and max_residual <= 1.0e-8
        and tensor_pass
        and zoh_pass
        and additive_pass
    )
    return {
        "nominal": nominal,
        "complement": complement,
        "quotient_levels": quotient_levels,
        "full_levels": full_levels,
        "selected": selected,
        "nominal_q": nominal_q,
        "additive": additive,
        "additive_singular_values": singular_values,
        "bilinear": bilinear,
        "scaling": scaling,
        "policy": policy,
        "gauge": gauge,
        "convergence": convergence,
        "zoh_checks": zoh_checks,
        "swing_checks": _swing_formula_checks(nominal, full_levels),
        "checks": {
            "mode_hash_all_equal": mode_pass,
            "name_hash_all_equal": name_pass,
            "maximum_equilibrium_residual": max_residual,
            "equilibrium_threshold": 1.0e-8,
            "tensor_richardson_pass": tensor_pass,
            "zoh_frechet_pass": zoh_pass,
            "additive_first_order_pass": additive_pass,
            "physical_parameter_tensor_valid": physical_pass,
            "smooth_normalized_policy_taylor_applicable": policy[
                "smooth_normalized_policy_taylor_applicable"
            ],
        },
    }


def run() -> None:
    seal = _verify_seal()
    if OUT.exists():
        raise FileExistsError(OUT)
    OUT.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    points = _parallel_points()
    analysis = _run_analysis(points)

    _json_new(
        OUT / "contracts/schema.json",
        {
            "round": ROUND,
            "parameter_names": list(u7.PARAMETER_NAMES),
            "parameter_units": ["GENCLS M"] * 4 + ["GENCLS D"] * 4,
            "joint_input_names": [f"energy_port_{i}" for i in range(1, 5)]
            + ["PQ_0", "PQ_1", "PQ_Bus14"],
            "output_names": [f"frequency_hz_{i}" for i in range(1, 5)],
            "sample_period_seconds": u7.DT,
            "horizon_steps": u7.HORIZON,
            "tensor_shapes": {
                "N": [8, 101, 101],
                "E": [8, 101, 7],
                "R": [8, 4, 101],
                "S": [8, 4, 7],
            },
            "N_E_R_S_meaning": "physical-unit derivatives of sampled post-observation quotient (A,B,C,D)",
            "normalized_action_warning": analysis["policy"]["reason"],
        },
    )
    point_index = []
    for point in points:
        arrays = point["arrays"]
        _npz_new(OUT / f"parameter_points/{point['point_id']}.npz", **arrays)
        point_index.append(
            {
                key: value
                for key, value in point.items()
                if key not in ("arrays", "names", "M_values", "D_values", "source_metrics")
            }
            | {
                "M_values": point["M_values"].tolist(),
                "D_values": point["D_values"].tolist(),
                "source_metrics": point["source_metrics"],
                "names": point["names"],
                "npz": f"parameter_points/{point['point_id']}.npz",
            }
        )
    _json_new(OUT / "parameter_points/index.json", point_index)
    _npz_new(
        OUT / "tensors/mixed_tensors.npz",
        N=analysis["selected"]["A_post"],
        E=analysis["selected"]["B_post"],
        R=analysis["selected"]["C_post"],
        S=analysis["selected"]["D_post"],
        N_continuous=analysis["selected"]["A_continuous"],
        E_continuous=analysis["selected"]["B_continuous"],
        R_continuous=analysis["selected"]["C_continuous"],
        S_continuous=analysis["selected"]["D_continuous"],
        parameter_names=np.asarray(u7.PARAMETER_NAMES),
        base_steps=u7.BASE_STEPS,
        levels=np.asarray(u7.LEVELS),
        gauge_complement=analysis["complement"],
    )
    level_arrays = {}
    for key, value in analysis["quotient_levels"].items():
        level_arrays[f"quotient_{key}"] = value
    for key, value in analysis["full_levels"].items():
        level_arrays[f"full_{key}"] = value
    _npz_new(OUT / "tensors/all_fd_levels.npz", **level_arrays)
    _npz_new(
        OUT / "lifts/additive_lift.npz",
        H=analysis["additive"],
        singular_values=analysis["additive_singular_values"],
        differential_basis=la.null_space(np.ones((1, 4))),
    )
    _npz_new(OUT / "lifts/bilinear_lift.npz", H=analysis["bilinear"])
    _json_new(OUT / "scaling/amplitude_scaling.json", analysis["scaling"])
    _json_new(OUT / "checks/richardson.json", analysis["convergence"])
    _json_new(OUT / "checks/zoh_frechet.json", analysis["zoh_checks"])
    _json_new(OUT / "checks/swing_formula.json", analysis["swing_checks"])
    _json_new(OUT / "checks/policy_and_decoder.json", analysis["policy"])
    verdict = (
        "PHYSICAL-TENSORS-VALID_NORMALIZED-TAYLOR-NOT-APPLICABLE"
        if analysis["checks"]["physical_parameter_tensor_valid"]
        else "LOCAL-TAYLOR-NOT-APPLICABLE"
    )
    verification = {
        "round": ROUND,
        "created_utc": _utc(),
        "formal_seal_sha256": _sha256(SEAL),
        "unique_parameter_points": len(points),
        "gauge": analysis["gauge"],
        **analysis["checks"],
        "additive_lift_shape": list(analysis["additive"].shape),
        "additive_sigma_max": float(analysis["additive_singular_values"][0]),
        "additive_sigma_min": float(analysis["additive_singular_values"][-1]),
        "additive_numerical_rank": int(np.linalg.matrix_rank(analysis["additive"])),
        "bilinear_lift_shape": list(analysis["bilinear"].shape),
        "r444_md_quadratic_blocks": sum(
            row["classification"] == "QUADRATIC" for row in analysis["scaling"]["blocks"]
        ),
        "r444_md_last_two_stable_blocks": sum(
            row["last_two_quadratic_stable_20pct"] for row in analysis["scaling"]["blocks"]
        ),
        "r444_md_linear_trend_down_blocks": sum(
            row["linear_normalized_trends_down"] for row in analysis["scaling"]["blocks"]
        ),
        "verdict": verdict,
        "all_required_artifacts_written": True,
    }
    _json_new(OUT / "checks/verification_report.json", verification)
    _json_new(OUT / "provenance/runtime.json", runtime_manifest(ROOT))
    _json_new(
        OUT / "claim_evidence_map.json",
        {
            "claim_id": "U7-local-quadratic-scaling",
            "scope": "Object A physical parameters, registered equilibrium, finite 30-step window",
            "status": "supported-qualified"
            if analysis["checks"]["physical_parameter_tensor_valid"]
            else "invalid",
            "raw_inputs": [
                {"path": _relative(R444), "sha256": _sha256(R444)},
                {"path": _relative(R446), "sha256": _sha256(R446)},
            ],
            "derived_fields": [
                {"path": "tensors/mixed_tensors.npz", "field": "N,E,R,S"},
                {"path": "lifts/additive_lift.npz", "field": "H,singular_values"},
                {"path": "lifts/bilinear_lift.npz", "field": "H"},
                {"path": "scaling/amplitude_scaling.json", "json_pointer": "/blocks"},
            ],
            "scripts": [
                {"path": row["path"], "sha256": row["sha256"]}
                for row in seal["sources"].values()
                if row["path"].endswith(".py")
            ],
            "independent_checks": [
                {
                    "path": "checks/zoh_frechet.json",
                    "status": "pass" if analysis["checks"]["zoh_frechet_pass"] else "fail",
                }
            ],
            "authorized_wording": "Physical-unit local tensors converge at the registered equilibrium; the sealed direct-M/D response is quadratic-leading over its measured ladder, while the additive port is first-order over the declared lift.",
            "prohibited_wording": [
                "A single C2 Taylor theorem applies to the normalized implemented policy",
                "global or robust second-order authority",
            ],
        },
    )

    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    lines = [f"{_sha256(path)}  {path.relative_to(OUT).as_posix()}" for path in files]
    (OUT / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {**verification, "wall_seconds": time.perf_counter() - start, "files": len(files) + 1},
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
