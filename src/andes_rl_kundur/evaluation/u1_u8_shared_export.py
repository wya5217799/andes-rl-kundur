"""Auditable shared Object A/Object B export for the U1--U8 program.

This module reconstructs existing governed objects.  It does not solve any of
the downstream mathematical questions and it does not run controller training.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from dataclasses import asdict
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any

import numpy as np
from scipy.signal import cont2discrete


LOAD_IDS = ("PQ_0", "PQ_1", "PQ_Bus14")
OBJECT_B_FD_STEPS = (1.0e-4, 1.0e-5, 1.0e-6)
OBJECT_A_FD_STEPS = (1.0e-2, 1.0e-3, 1.0e-4)
SAMPLE_PERIOD_SECONDS = 0.2
NOMINAL_FREQUENCY_HZ = 60.0
BANDPASS_CONTRACT = {"f0_hz": 0.4, "zeta": 0.35, "dt": 0.2, "gain": 3.5}
LOCAL_PI_CONTRACT = {"kp_normalized_per_hz": 4.0, "ki_normalized_per_hz_second": 0.8}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, complex):
        return {"real": float(value.real), "imag": float(value.imag)}
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def write_json_new(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(_jsonable(payload), stream, indent=2, ensure_ascii=False, sort_keys=True)
        stream.write("\n")


def write_text_new(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def write_npz_new(path: Path, **arrays: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    with path.open("xb") as stream:
        np.savez_compressed(stream, **{name: np.asarray(value) for name, value in arrays.items()})


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=root, check=True, text=True, encoding="utf-8",
        errors="replace", stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return completed.stdout


def runtime_manifest(root: Path) -> dict[str, Any]:
    import andes

    case_path = Path(andes.get_case("kundur/kundur_full.xlsx")).resolve()
    versions: dict[str, str] = {}
    for name in ("andes", "numpy", "scipy", "pandas", "torch", "gymnasium"):
        try:
            versions[name] = importlib_metadata.version(name)
        except importlib_metadata.PackageNotFoundError:
            versions[name] = "not-installed"
    return {
        "git_commit": _git(root, "rev-parse", "HEAD").strip(),
        "git_branch": _git(root, "rev-parse", "--abbrev-ref", "HEAD").strip(),
        "git_status_porcelain": _git(root, "status", "--porcelain=v1", "--untracked-files=all").splitlines(),
        "python": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "packages": versions,
        "andes_module": str(Path(andes.__file__).resolve()),
        "case_path": str(case_path),
        "case_sha256": sha256_file(case_path),
        "numpy_blas_configuration": _numpy_configuration(),
        "rng_contract": {
            "environment_seed": 42,
            "finite_difference": "deterministic central difference",
            "training": "not executed",
        },
        "thread_contract": {
            "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS", "unset"),
            "OPENBLAS_NUM_THREADS": os.environ.get("OPENBLAS_NUM_THREADS", "unset"),
            "MKL_NUM_THREADS": os.environ.get("MKL_NUM_THREADS", "unset"),
            "NUMEXPR_NUM_THREADS": os.environ.get("NUMEXPR_NUM_THREADS", "unset"),
        },
    }


def _numpy_configuration() -> str:
    from io import StringIO
    from contextlib import redirect_stdout

    stream = StringIO()
    with redirect_stdout(stream):
        np.show_config()
    return stream.getvalue()


def _build_v4_env() -> Any:
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4

    env = AndesMultiVSGEnvV4(
        random_disturbance=False, comm_fail_prob=0.0, comm_delay_steps=0
    )
    env.seed(42)
    return env


def _headroom() -> tuple[np.ndarray, dict[str, Any]]:
    from andes_rl_kundur.control.active_power import r272_frozen_bess_contract

    contract = r272_frozen_bess_contract()
    lower, upper = contract.feasible_power_bounds(
        previous_power_system_pu=np.zeros(4, dtype=float),
        soc=np.full(4, float(contract.soc_initial), dtype=float),
        voltage_pu=np.ones(4, dtype=float),
        dt_seconds=SAMPLE_PERIOD_SECONDS,
    )
    fields = {
        key: value
        for key, value in asdict(contract).items()
        if isinstance(value, (str, int, float, bool, tuple, list))
    }
    return np.asarray(upper, dtype=float), {
        "producer_round": "R272",
        "contract": fields,
        "equilibrium_previous_power_system_pu": [0.0] * 4,
        "equilibrium_soc": [float(contract.soc_initial)] * 4,
        "equilibrium_voltage_pu": [1.0] * 4,
        "lower_system_pu": np.asarray(lower, dtype=float),
        "upper_system_pu": np.asarray(upper, dtype=float),
        "active_mode": "positive_headroom_about_zero_anchor",
    }


def _controller_arrays(sampled: Any, headroom: np.ndarray) -> dict[str, np.ndarray]:
    from andes_rl_kundur.control.ring_bandpass_damping import (
        prewarped_bandpass_coefficients,
        ring_incidence,
    )

    num, den = prewarped_bandpass_coefficients(**BANDPASS_CONTRACT)
    b0, b1, b2 = (float(value) for value in num)
    a1, a2 = float(den[1]), float(den[2])
    incidence = ring_incidence(4)
    bt = incidence.T
    ad = sampled.state_matrix
    bc = sampled.input_matrix[:, :4] @ np.diag(headroom)
    bd = sampled.input_matrix[:, 4:]
    cw = sampled.output_matrix
    nx = ad.shape[0]
    bandpass_a = np.block(
        [
            [ad - b0 * (bc @ incidence @ bt @ cw), -(bc @ incidence), np.zeros((nx, 4))],
            [(b1 - a1 * b0) * (bt @ cw), -a1 * np.eye(4), np.eye(4)],
            [(b2 - a2 * b0) * (bt @ cw), -a2 * np.eye(4), np.zeros((4, 4))],
        ]
    )
    bandpass_b = np.vstack([bd, np.zeros((8, 3))])
    bandpass_c = np.hstack([cw, np.zeros((4, 8))])
    kp = LOCAL_PI_CONTRACT["kp_normalized_per_hz"]
    ki = LOCAL_PI_CONTRACT["ki_normalized_per_hz_second"]
    local_a = np.block(
        [
            [ad - kp * (bc @ cw), bc],
            [-ki * SAMPLE_PERIOD_SECONDS * cw, np.eye(4)],
        ]
    )
    local_b = np.vstack([bd, np.zeros((4, 3))])
    local_c = np.hstack([cw, np.zeros((4, 4))])
    return {
        "bandpass_numerator": np.asarray(num, dtype=float),
        "bandpass_denominator": np.asarray(den, dtype=float),
        "ring_incidence": incidence,
        "headroom_system_pu": headroom,
        "bandpass_A_cl": bandpass_a,
        "bandpass_B_disturbance_cl": bandpass_b,
        "bandpass_C_frequency_cl": bandpass_c,
        "local_pi_A_cl": local_a,
        "local_pi_B_disturbance_cl": local_b,
        "local_pi_C_frequency_cl": local_c,
    }


def build_object_b() -> dict[str, Any]:
    from andes_rl_kundur.evaluation.model_first_input_bridge import (
        fold_zero_time_constant_states,
        reduce_folded_descriptor,
    )
    from andes_rl_kundur.evaluation.vsg_energy_port_source_adapter import (
        AndesVSGEnergyPortFixedStateSource,
    )
    from andes_rl_kundur.evaluation.vsg_energy_port_source_bridge import (
        derive_vsg_energy_port_input_bridge,
    )
    from andes_rl_kundur.evaluation.vsg_energy_port_source_model import (
        construct_vsg_energy_port_source_model,
    )
    from andes_rl_kundur.env.andes.vsg_energy_port_env import AndesVSGEnergyPortEnv

    base = _build_v4_env()
    env = AndesVSGEnergyPortEnv(base_env=base)
    try:
        env.reset(delta_u={})
        source = AndesVSGEnergyPortFixedStateSource.from_initialized_energy_port_env(
            env, pq_load_ids=LOAD_IDS, source_fingerprint="R459:R447-contract"
        )
        bridges = tuple(
            derive_vsg_energy_port_input_bridge(
                binding=source.binding, source=source, step_system_pu=step
            )
            for step in OBJECT_B_FD_STEPS
        )
        result = construct_vsg_energy_port_source_model(
            snapshot=source.descriptor_snapshot, bridges=bridges
        )
        if not result.passed or result.sampled_model is None:
            raise RuntimeError(f"Object B source gate failed: {result.error}")
        snap = source.descriptor_snapshot
        selected = bridges[-1]
        folded = fold_zero_time_constant_states(
            time_constants=snap.time_constants,
            f_x=snap.f_x,
            f_y=snap.f_y,
            g_x=snap.g_x,
            g_y=snap.g_y,
            f_input=selected.joint_f_input,
            g_input=selected.joint_g_input,
        )
        reduced = reduce_folded_descriptor(folded, minimum_reciprocal_condition=1.0e-12)
        c_cont = snap.frequency_output_map[:, folded.dynamic_state_indices]
        d_cont = np.zeros((4, 7), dtype=float)
        ad, bd, c_pre, d_pre, _ = cont2discrete(
            (reduced.state_matrix, reduced.input_matrix, c_cont, d_cont),
            SAMPLE_PERIOD_SECONDS, method="zoh"
        )
        sampled = result.sampled_model
        headroom, headroom_contract = _headroom()
        return {
            "dae": {
                "time_constants": snap.time_constants,
                "f_x": snap.f_x,
                "f_y": snap.f_y,
                "g_x": snap.g_x,
                "g_y": snap.g_y,
                "equilibrium_x": snap.equilibrium_x,
                "equilibrium_y": snap.equilibrium_y,
                "equilibrium_z": snap.equilibrium_z,
                "equilibrium_f": snap.equilibrium_f,
                "equilibrium_g": snap.equilibrium_g,
                "eig_state_matrix": snap.eig_state_matrix,
                "eig_eigenvalues": snap.eig_eigenvalues,
                "frequency_output_map_full": snap.frequency_output_map,
                "omega_state_addresses": snap.omega_state_addresses,
            },
            "bridges": {
                "steps": np.asarray(OBJECT_B_FD_STEPS),
                "control_f_input": np.stack([item.control.f_input for item in bridges]),
                "control_g_input": np.stack([item.control.g_input for item in bridges]),
                "control_midpoint_ratios": np.stack([item.control.midpoint_ratios for item in bridges]),
                "disturbance_f_input": np.stack([item.disturbance.f_input for item in bridges]),
                "disturbance_g_input": np.stack([item.disturbance.g_input for item in bridges]),
                "disturbance_midpoint_ratios": np.stack([item.disturbance.midpoint_ratios for item in bridges]),
                "power_to_tm0_jacobian": selected.power_to_tm0_jacobian,
            },
            "continuous": {
                "E_d": folded.e_d,
                "F_x": folded.f_x,
                "F_algebraic": folded.f_algebraic,
                "G_x": folded.g_x,
                "G_algebraic": folded.g_algebraic,
                "F_input": folded.f_input,
                "G_input": folded.g_input,
                "dynamic_state_indices": folded.dynamic_state_indices,
                "folded_state_indices": folded.folded_state_indices,
                "A_continuous": reduced.state_matrix,
                "B_continuous": reduced.input_matrix,
                "C_frequency_continuous": c_cont,
                "D_continuous": d_cont,
            },
            "sampled": {
                "A_pre_zoh": np.asarray(ad, dtype=float),
                "B_pre_zoh": np.asarray(bd, dtype=float),
                "C_pre_zoh": np.asarray(c_pre, dtype=float),
                "D_pre_zoh": np.asarray(d_pre, dtype=float),
                "A_post_step": sampled.state_matrix,
                "B_post_step": sampled.input_matrix,
                "C_post_step": sampled.output_matrix,
                "D_post_step": sampled.feedthrough_matrix,
                "sample_period_seconds": np.asarray(SAMPLE_PERIOD_SECONDS),
            },
            "controllers": _controller_arrays(sampled, headroom),
            "metadata": {
                "object_id": "Object B",
                "producer_round": "R459",
                "source_contract_rounds": ["R272", "R447"],
                "state_names": snap.state_names,
                "algebraic_names": snap.algebraic_names,
                "dynamic_state_names": result.dynamic_state_names,
                "input_names": [
                    "delta_pref_vsg_1_system_pu", "delta_pref_vsg_2_system_pu",
                    "delta_pref_vsg_3_system_pu", "delta_pref_vsg_4_system_pu",
                    "delta_PQ_0_system_pu", "delta_PQ_1_system_pu", "delta_PQ_Bus14_system_pu",
                ],
                "output_names": [f"vsg_{index}_frequency_hz" for index in range(1, 5)],
                "binding": asdict(source.binding),
                "baseline_pref_system_pu": np.asarray(source._baseline_pref_system_pu),
                "baseline_load_system_pu": source.baseline_load_system_pu,
                "initialization_residual_tolerance": snap.initialization_residual_tolerance,
                "initialization_max_abs_f": snap.initialization_max_abs_f,
                "initialization_max_abs_g": snap.initialization_max_abs_g,
                "positive_real_tolerance": snap.positive_real_tolerance,
                "positive_real_count": snap.positive_real_count,
                "source_gate_metrics": result.metrics,
                "selected_fd_step_system_pu": OBJECT_B_FD_STEPS[-1],
                "derivative_scheme": selected.control.scheme,
                "observation_convention": "end-of-held-input interval; C_post=C_pre A_d, D_post=C_pre B_d+D_pre",
                "units": {
                    "control_input": "system pu active power command",
                    "disturbance_input": "system pu PQ active power",
                    "output": "Hz on 60-Hz base",
                    "sample_period": "seconds",
                },
                "bandpass_contract": BANDPASS_CONTRACT,
                "local_pi_contract": LOCAL_PI_CONTRACT,
                "headroom": headroom_contract,
            },
        }
    finally:
        env.close()


def _object_a_snapshot(env: Any) -> dict[str, Any]:
    from andes_rl_kundur.evaluation.r405_linearization import dense_matrix

    ss = env.ss
    models = ss.exist.pflow_tds
    ss.TDS.fg_update(models=models)
    ss.j_update(models=models, info="R459 Object A shared export")
    positions = list(env._vsg_pos)
    return {
        "models": models,
        "positions": positions,
        "vsg_ids": list(env.vsg_idx),
        "m_base": np.asarray([ss.GENCLS.M.v[p] for p in positions], dtype=float),
        "d_base": np.asarray([ss.GENCLS.D.v[p] for p in positions], dtype=float),
        "omega": np.asarray([ss.GENCLS.omega.v[p] for p in positions], dtype=float),
        "omega_addresses": np.asarray([ss.GENCLS.omega.a[p] for p in positions], dtype=int),
        "time_constants": np.asarray(ss.dae.Tf, dtype=float).copy(),
        "f_x": dense_matrix(ss.dae.fx), "f_y": dense_matrix(ss.dae.fy),
        "g_x": dense_matrix(ss.dae.gx), "g_y": dense_matrix(ss.dae.gy),
        "x": np.asarray(ss.dae.x, dtype=float).copy(),
        "y": np.asarray(ss.dae.y, dtype=float).copy(),
        "z": np.asarray(ss.dae.z, dtype=float).copy(),
        "f": np.asarray(ss.dae.f, dtype=float).copy(),
        "g": np.asarray(ss.dae.g, dtype=float).copy(),
        "state_names": [str(value) for value in ss.dae.x_name],
        "algebraic_names": [str(value) for value in ss.dae.y_name],
        "residual_tolerance": float(ss.TDS.config.tol),
    }


def _object_a_callback(env: Any, snap: dict[str, Any]):
    ss = env.ss

    def callback(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        values = np.asarray(values, dtype=float)
        if values.shape != (8,):
            raise ValueError("Object A input must have shape (8,)")
        for index, device_id in enumerate(snap["vsg_ids"]):
            ss.GENCLS.set("M", device_id, float(values[index]), attr="v")
            ss.GENCLS.set("D", device_id, float(values[4 + index]), attr="v")
        ss.TDS.fg_update(models=snap["models"])
        f_value = np.asarray(ss.dae.f, dtype=float).copy()
        g_value = np.asarray(ss.dae.g, dtype=float).copy()
        for index, device_id in enumerate(snap["vsg_ids"]):
            ss.GENCLS.set("M", device_id, float(snap["m_base"][index]), attr="v")
            ss.GENCLS.set("D", device_id, float(snap["d_base"][index]), attr="v")
        return f_value, g_value

    return callback


def build_object_a() -> dict[str, Any]:
    from andes_rl_kundur.env.andes.model_first_contract import finite_difference_input_jacobians

    env = _build_v4_env()
    try:
        env.reset(delta_u={})
        snap = _object_a_snapshot(env)
        callback = _object_a_callback(env, snap)
        centre = np.concatenate([snap["m_base"], snap["d_base"]])
        jacobians = [
            finite_difference_input_jacobians(callback, equilibrium_input=centre, step=step)
            for step in OBJECT_A_FD_STEPS
        ]
        b_stack = np.stack(
            [jac.f_input - snap["f_y"] @ np.linalg.solve(snap["g_y"], jac.g_input)
             for jac in jacobians]
        )
        positive_scales = np.full(8, 600.0, dtype=float)
        negative_scales = np.full(8, 200.0, dtype=float)
        selected_b = b_stack[-1]
        return {
            "dae": {
                "time_constants": snap["time_constants"],
                "f_x": snap["f_x"], "f_y": snap["f_y"],
                "g_x": snap["g_x"], "g_y": snap["g_y"],
                "equilibrium_x": snap["x"], "equilibrium_y": snap["y"],
                "equilibrium_z": snap["z"], "equilibrium_f": snap["f"],
                "equilibrium_g": snap["g"], "omega": snap["omega"],
                "omega_state_addresses": snap["omega_addresses"],
                "baseline_M": snap["m_base"], "baseline_D": snap["d_base"],
            },
            "maps": {
                "fd_steps_physical": np.asarray(OBJECT_A_FD_STEPS),
                "f_input_physical_stack": np.stack([jac.f_input for jac in jacobians]),
                "g_input_physical_stack": np.stack([jac.g_input for jac in jacobians]),
                "midpoint_ratios_stack": np.stack([jac.midpoint_ratios for jac in jacobians]),
                "B_u_r_physical_stack": b_stack,
                "normalized_positive_physical_scale": positive_scales,
                "normalized_negative_physical_scale": negative_scales,
                "B_u_r_normalized_positive": selected_b @ np.diag(positive_scales),
                "B_u_r_normalized_negative": selected_b @ np.diag(negative_scales),
                "env_interleaved_to_export_grouped": np.asarray([0, 4, 1, 5, 2, 6, 3, 7], dtype=int),
            },
            "metadata": {
                "object_id": "Object A",
                "producer_round": "R459",
                "source_contract_round": "R446",
                "actuator": "four GENCLS direct M/D parameter modulation",
                "state_names": snap["state_names"],
                "algebraic_names": snap["algebraic_names"],
                "physical_input_names_grouped": [f"M_{i}" for i in range(1, 5)] + [f"D_{i}" for i in range(1, 5)],
                "normalized_input_names_grouped": [f"normalized_delta_M_{i}" for i in range(1, 5)] + [f"normalized_delta_D_{i}" for i in range(1, 5)],
                "environment_action_order": [f"agent_{i}_[normalized_delta_M,normalized_delta_D]" for i in range(1, 5)],
                "mapping": {
                    "positive": "delta_M=600*a_M and delta_D=600*a_D for a>=0",
                    "negative": "delta_M=200*a_M and delta_D=200*a_D for a<0",
                    "physical": "M=max(200+delta_M,20); D=max(100+delta_D,10)",
                    "nondifferentiability": "normalized mapping has distinct one-sided derivatives at zero",
                },
                "execution": {
                    "raw_target_bounds": [-1.0, 1.0],
                    "per_vsg_projector_slew_limit_per_step": 0.25,
                    "projector_previous_action_reset": [0.0, 0.0],
                    "projector_previous_action_update": "store executed projected float32 action",
                    "environment_internal_slew": "none; parameter transition is interpolated over N_SUBSTEPS=5",
                    "control_period_seconds": 0.2,
                    "replay_requirement_for_successor": "store raw target and executed projected action separately; replay/critic/target must use executed action",
                },
                "units": {
                    "M": "GENCLS M=2H seconds on device model",
                    "D": "GENCLS damping parameter per unit",
                    "normalized_action": "dimensionless",
                },
                "finite_difference_scheme": "central at frozen x,y",
                "selected_fd_step_physical": OBJECT_A_FD_STEPS[-1],
                "residual_tolerance": snap["residual_tolerance"],
                "max_abs_f": float(np.max(np.abs(snap["f"]))),
                "max_abs_g": float(np.max(np.abs(snap["g"]))),
                "max_abs_omega_deviation_pu": float(np.max(np.abs(snap["omega"] - 1.0))),
                "gy_condition_2": float(np.linalg.cond(snap["g_y"])),
            },
        }
    finally:
        env.close()


def write_model_bundle(out: Path, object_a: dict[str, Any], object_b: dict[str, Any]) -> None:
    if out.exists():
        raise FileExistsError(f"formal output already exists: {out}")
    out.mkdir(parents=True, exist_ok=False)
    a_root = out / "model_exports/object_a"
    b_root = out / "model_exports/object_b"
    write_npz_new(a_root / "dae_snapshot.npz", **object_a["dae"])
    write_npz_new(a_root / "input_output_maps.npz", **object_a["maps"])
    write_json_new(a_root / "execution_contract.json", object_a["metadata"]["execution"])
    write_json_new(a_root / "metadata.json", object_a["metadata"])
    write_npz_new(b_root / "dae_snapshot.npz", **object_b["dae"])
    write_npz_new(b_root / "input_bridges.npz", **object_b["bridges"])
    write_npz_new(b_root / "continuous_reduced_model.npz", **object_b["continuous"])
    write_npz_new(b_root / "sampled_model.npz", **object_b["sampled"])
    write_npz_new(b_root / "controllers.npz", **object_b["controllers"])
    write_json_new(b_root / "headroom_modes.json", object_b["metadata"]["headroom"])
    write_json_new(b_root / "metadata.json", object_b["metadata"])


def _max_abs(values: np.ndarray) -> float:
    return float(np.max(np.abs(np.asarray(values, dtype=float))))


def verify_model_bundle(out: Path) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    a_dae = np.load(out / "model_exports/object_a/dae_snapshot.npz", allow_pickle=False)
    a_maps = np.load(out / "model_exports/object_a/input_output_maps.npz", allow_pickle=False)
    b_dae = np.load(out / "model_exports/object_b/dae_snapshot.npz", allow_pickle=False)
    b_cont = np.load(out / "model_exports/object_b/continuous_reduced_model.npz", allow_pickle=False)
    b_sampled = np.load(out / "model_exports/object_b/sampled_model.npz", allow_pickle=False)
    a_meta = json.loads((out / "model_exports/object_a/metadata.json").read_text(encoding="utf-8"))
    b_meta = json.loads((out / "model_exports/object_b/metadata.json").read_text(encoding="utf-8"))

    arrays = [*a_dae.values(), *a_maps.values(), *b_dae.values(), *b_cont.values(), *b_sampled.values()]
    checks["all_arrays_finite"] = all(np.all(np.isfinite(value)) for value in arrays)
    checks["object_a_dimensions"] = (
        a_maps["f_input_physical_stack"].shape[0] == 3
        and a_maps["f_input_physical_stack"].shape[2] == 8
        and a_maps["g_input_physical_stack"].shape[2] == 8
        and a_maps["B_u_r_physical_stack"].shape[2] == 8
        and len(a_meta["physical_input_names_grouped"]) == 8
    )
    a_b_recomputed = np.stack([
        a_maps["f_input_physical_stack"][index]
        - a_dae["f_y"] @ np.linalg.solve(a_dae["g_y"], a_maps["g_input_physical_stack"][index])
        for index in range(3)
    ])
    checks["object_a_schur_max_abs_error"] = _max_abs(a_b_recomputed - a_maps["B_u_r_physical_stack"])
    selected_a = a_maps["B_u_r_physical_stack"][-1]
    checks["object_a_positive_mapping_max_abs_error"] = _max_abs(
        selected_a @ np.diag(a_maps["normalized_positive_physical_scale"])
        - a_maps["B_u_r_normalized_positive"]
    )
    checks["object_a_negative_mapping_max_abs_error"] = _max_abs(
        selected_a @ np.diag(a_maps["normalized_negative_physical_scale"])
        - a_maps["B_u_r_normalized_negative"]
    )
    checks["object_a_equilibrium"] = (
        float(a_meta["max_abs_omega_deviation_pu"]) <= 1.0e-6
        and float(a_meta["gy_condition_2"]) < 1.0e10
    )

    eliminated_x = np.linalg.solve(b_cont["G_algebraic"], b_cont["G_x"])
    eliminated_u = np.linalg.solve(b_cont["G_algebraic"], b_cont["G_input"])
    a_recomputed = np.linalg.solve(
        b_cont["E_d"], b_cont["F_x"] - b_cont["F_algebraic"] @ eliminated_x
    )
    b_recomputed = np.linalg.solve(
        b_cont["E_d"], b_cont["F_input"] - b_cont["F_algebraic"] @ eliminated_u
    )
    checks["object_b_A_reduction_max_abs_error"] = _max_abs(a_recomputed - b_cont["A_continuous"])
    checks["object_b_B_reduction_max_abs_error"] = _max_abs(b_recomputed - b_cont["B_continuous"])
    checks["object_b_dimensions"] = (
        b_cont["B_continuous"].shape[1] == 7
        and b_cont["C_frequency_continuous"].shape[0] == 4
        and len(b_meta["input_names"]) == 7
        and len(b_meta["output_names"]) == 4
    )
    checks["object_b_equilibrium"] = (
        float(b_meta["initialization_max_abs_f"]) < float(b_meta["initialization_residual_tolerance"])
        and float(b_meta["initialization_max_abs_g"]) < float(b_meta["initialization_residual_tolerance"])
        and int(b_meta["positive_real_count"]) == 0
    )
    checks["zoh_A_max_abs_error"] = _max_abs(b_sampled["A_post_step"] - b_sampled["A_pre_zoh"])
    checks["zoh_B_max_abs_error"] = _max_abs(b_sampled["B_post_step"] - b_sampled["B_pre_zoh"])
    checks["zoh_C_post_identity_max_abs_error"] = _max_abs(
        b_sampled["C_post_step"] - b_sampled["C_pre_zoh"] @ b_sampled["A_pre_zoh"]
    )
    checks["zoh_D_post_identity_max_abs_error"] = _max_abs(
        b_sampled["D_post_step"]
        - (b_sampled["C_pre_zoh"] @ b_sampled["B_pre_zoh"] + b_sampled["D_pre_zoh"])
    )
    checks["object_reference_separation"] = (
        a_meta["object_id"] == "Object A"
        and b_meta["object_id"] == "Object B"
        and a_meta["source_contract_round"] != b_meta["source_contract_rounds"][-1]
    )
    numeric_limits = [
        "object_a_schur_max_abs_error", "object_a_positive_mapping_max_abs_error",
        "object_a_negative_mapping_max_abs_error", "object_b_A_reduction_max_abs_error",
        "object_b_B_reduction_max_abs_error", "zoh_A_max_abs_error", "zoh_B_max_abs_error",
        "zoh_C_post_identity_max_abs_error", "zoh_D_post_identity_max_abs_error",
    ]
    checks["numeric_tolerance_1e_10"] = all(float(checks[name]) <= 1.0e-10 for name in numeric_limits)
    boolean_names = [
        "all_arrays_finite", "object_a_dimensions", "object_a_equilibrium",
        "object_b_dimensions", "object_b_equilibrium", "object_reference_separation",
        "numeric_tolerance_1e_10",
    ]
    passed = all(bool(checks[name]) for name in boolean_names)
    return {
        "schema_version": 1,
        "round": "R459",
        "independent_checker": "reads emitted NPZ/JSON and recomputes identities",
        "checks": checks,
        "passed": passed,
        "verdict": "SHARED-MODEL-EXPORT-VALID" if passed else "SHARED-MODEL-EXPORT-INVALID",
    }


def write_sha256sums(out: Path, *, excluded: tuple[str, ...] = ("SHA256SUMS", "checks/verification_report.json")) -> int:
    excluded_set = set(excluded)
    paths = sorted(
        path for path in out.rglob("*")
        if path.is_file() and path.relative_to(out).as_posix() not in excluded_set
    )
    lines = [f"{sha256_file(path)}  {path.relative_to(out).as_posix()}" for path in paths]
    write_text_new(out / "SHA256SUMS", "\n".join(lines) + "\n")
    return len(lines)


def verify_sha256sums(out: Path) -> dict[str, Any]:
    lines = (out / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    failures: list[str] = []
    for line in lines:
        expected, relative = line.split("  ", 1)
        path = out / relative
        if not path.is_file() or sha256_file(path) != expected:
            failures.append(relative)
    return {"entries": len(lines), "failures": failures, "passed": not failures}


__all__ = [
    "build_object_a", "build_object_b", "runtime_manifest", "sha256_file",
    "verify_model_bundle", "verify_sha256sums", "write_json_new", "write_model_bundle",
    "write_npz_new", "write_sha256sums", "write_text_new",
]
